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
<p>You're on the Promptiv list.</p>
<p>Promptiv finds trips hiding in your budget. Tell us what you have to spend and how many days you have, and we'll surface 5-8 ideas with the catch on each.</p>
<p><a href="https://promptiv.io/go" style="color:#a78bfa;font-weight:600;">Try it now &rarr;</a></p>
<p>We'll email you when prices shift on trips you've explored and when new features ship. No spam.</p>
<p>&mdash; Adam</p>
<p style="color:#888;font-size:12px;">To unsubscribe, reply with the word UNSUBSCRIBE.</p>
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
