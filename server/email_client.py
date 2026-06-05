"""Resend email wrapper for Promptiv teaser confirmations.

Failures are logged but never raised — a transient email failure must not
block signup.
"""
import logging
import os
from typing import Any, Optional

import resend


logger = logging.getLogger(__name__)


CONFIRMATION_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1.0" />
<title>You're on the Promptiv list</title>
</head>
<body style="margin:0;padding:0;background:#f5f3ee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f5f3ee;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;background:#ffffff;border-radius:14px;border:1px solid #ece9e1;">
          <tr>
            <td style="padding:36px 36px 8px 36px;">
              <div style="font-family:Georgia,'Times New Roman',serif;font-size:24px;font-weight:400;color:#1a1a1f;letter-spacing:-0.01em;">
                Promptiv<span style="display:inline-block;width:6px;height:6px;background:#a78bfa;border-radius:50%;margin-left:5px;vertical-align:middle;transform:translateY(-6px);"></span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 36px 28px 36px;color:#2a2a32;font-size:15.5px;line-height:1.6;">
              <p style="margin:18px 0 18px;font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:22px;color:#1a1a1f;line-height:1.25;">
                You're on the list.
              </p>
              <p style="margin:0 0 18px;color:#3a3a42;">
                Promptiv finds trips hiding in your budget. Tell us what you have to spend and how many days you have, and we'll surface 5–8 ideas with the catch on each.
              </p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 14px;">
                <tr>
                  <td bgcolor="#a78bfa" style="border-radius:10px;">
                    <a href="https://promptiv.io/go" style="display:inline-block;padding:13px 26px;color:#0a0a0e;text-decoration:none;font-weight:600;font-size:14.5px;letter-spacing:0.01em;">Try it now &rarr;</a>
                  </td>
                </tr>
              </table>
              <p style="margin:18px 0 18px;color:#5a5a62;font-size:13.5px;">
                We'll email you when new features ship. No spam, no inbox noise.
              </p>
              <p style="margin:0;color:#1a1a1f;font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:15.5px;">
                — Adam
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 36px;border-top:1px solid #ece9e1;color:#8a8a92;font-size:11.5px;line-height:1.55;">
              To unsubscribe, reply with the word UNSUBSCRIBE.<br />
              &copy; 2026 Promptiv &middot; <a href="https://promptiv.io/privacy" style="color:#8a8a92;text-decoration:underline;">Privacy</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

CONFIRMATION_TEXT = """\
You're on the Promptiv list.

Promptiv finds trips hiding in your budget. Tell us what you have to spend and
how many days you have, and we'll surface 5-8 ideas with the catch on each.

Try it now: https://promptiv.io/go

We'll email you when new features ship. No spam, no inbox noise.

— Adam

To unsubscribe, reply with the word UNSUBSCRIBE.
"""


def compose_welcome_email(to_email: str) -> dict:
    """Return a Resend-compatible payload (does not send). Used by /go email gate."""
    return {
        "to": [to_email],
        "from": os.environ.get("RESEND_FROM", "team@mail.distillworks.com"),
        "subject": "You're on the Promptiv list",
        "html": CONFIRMATION_HTML,
        "text": CONFIRMATION_TEXT,
    }


def send_confirmation(email: str) -> Optional[Any]:
    """Send the post-signup confirmation. Returns Resend response on success, None on failure."""
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM")
    if not api_key or not sender:
        logger.error("RESEND_API_KEY or RESEND_FROM not set; skipping email")
        return None

    resend.api_key = api_key
    payload = {
        "from": sender,
        "to": [email],
        "subject": "You're on the list.",
        "html": CONFIRMATION_HTML,
        "text": CONFIRMATION_TEXT,
    }
    reply_to = os.environ.get("RESEND_REPLY_TO")
    if reply_to:
        payload["reply_to"] = [reply_to]

    try:
        # Resend's SendParams is a TypedDict; building it dynamically (with conditional
        # reply_to) doesn't satisfy strict TypedDict checks.
        return resend.Emails.send(payload)  # type: ignore[arg-type]
    except Exception as e:
        logger.exception("Resend send failed: %s", e)
        return None


def send_pairing_alert(at_risk_list: list, to_email: Optional[str] = None) -> Optional[Any]:
    """Notify the operator that one or more pairing claims need a human look.

    The fact monitor calls this after each refresh with the output of
    pairings.at_risk(). No-op (returns None) when nothing is at risk or no
    recipient is configured — the alert is internal, so a missing address just
    means "don't bother me," not an error worth raising.
    """
    if not at_risk_list:
        return None
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM")
    recipient = (
        to_email
        or os.environ.get("PAIRING_ALERT_TO")
        or os.environ.get("RESEND_REPLY_TO")
    )
    if not api_key or not sender or not recipient:
        logger.warning(
            "pairing alert skipped: need RESEND_API_KEY, RESEND_FROM, and a recipient"
        )
        return None

    lines = [
        f"  {p['origin']}: {p['cheap_iata']} vs {p['anchor_iata']} "
        f"— {p['reason']} (margin ${p.get('margin_usd')})"
        for p in at_risk_list
    ]
    body = (
        "These pairing claims broke or got thin against the latest fares. "
        "Re-pair or re-verify:\n\n" + "\n".join(lines) + "\n"
    )
    resend.api_key = api_key
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": f"Promptiv: {len(at_risk_list)} pairing claim(s) need review",
        "text": body,
    }
    try:
        return resend.Emails.send(payload)  # type: ignore[arg-type]
    except Exception as e:
        logger.exception("pairing alert send failed: %s", e)
        return None


def send_digest_email(to_email: str, subject: str, html: str, text: str,
                      unsubscribe_url: Optional[str] = None) -> Optional[Any]:
    """Send one weekly digest. Sets the List-Unsubscribe header (RFC 8058
    one-click) for deliverability. Returns the Resend response or None on failure."""
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM")
    if not api_key or not sender:
        logger.error("RESEND_API_KEY or RESEND_FROM not set; skipping digest send")
        return None

    resend.api_key = api_key
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if unsubscribe_url:
        payload["headers"] = {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    reply_to = os.environ.get("RESEND_REPLY_TO")
    if reply_to:
        payload["reply_to"] = [reply_to]
    try:
        return resend.Emails.send(payload)  # type: ignore[arg-type]
    except Exception as e:
        logger.exception("digest send failed: %s", e)
        return None
