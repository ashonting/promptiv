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
                We'll email you when prices shift on trips you've explored and when new features ship. No spam.
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

We'll email you when prices shift on trips you've explored and when new features
ship. No spam.

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
