"""
Custom Django email backend that delivers via Resend REST API.
Configure EMAIL_BACKEND = "notifications.resend_backend.ResendEmailBackend"
and set RESEND_API_KEY in env.
"""
import logging
import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    def open(self): pass
    def close(self): pass

    def send_messages(self, email_messages):
        resend.api_key = settings.RESEND_API_KEY
        sent = 0
        for msg in email_messages:
            try:
                html = None
                if hasattr(msg, "alternatives"):
                    for content, mime in msg.alternatives:
                        if mime == "text/html":
                            html = content
                            break
                params = {
                    "from": msg.from_email,
                    "to": msg.to,
                    "subject": msg.subject,
                    "text": msg.body,
                }
                if html:
                    params["html"] = html
                resend.Emails.send(params)
                sent += 1
            except Exception as e:
                logger.error(f"[RESEND] Failed to send to {msg.to}: {e}")
                if not self.fail_silently:
                    raise
        return sent
