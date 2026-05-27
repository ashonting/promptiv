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
<p>You're on the list.</p>
<p>We're building Promptiv now. When we have something to show you, you'll be among the first to see it.</p>
<p>— The Promptiv team</p>
<p style="color:#888;font-size:12px;">To unsubscribe, reply with the word UNSUBSCRIBE.</p>
"""

CONFIRMATION_TEXT = """\
You're on the list.

We're building Promptiv now. When we have something to show you, you'll be among the first to see it.

— The Promptiv team

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
