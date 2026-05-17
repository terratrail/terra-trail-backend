"""
Custom Django email backend that delivers via Resend REST API.
Configure:
    EMAIL_BACKEND = "notifications.resend_backend.ResendEmailBackend"
    RESEND_API_KEY = "re_..."
    MAIL_DOMAIN = "mail.yourdomain.com"  (must be verified in Resend dashboard)
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
        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            logger.error("[RESEND] RESEND_API_KEY is not configured — emails will not be sent.")
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not set")
            return 0

        resend.api_key = api_key
        sent = 0

        for msg in email_messages:
            try:
                html = None
                if hasattr(msg, "alternatives"):
                    for content, mime in msg.alternatives:
                        if mime == "text/html":
                            html = content
                            break

                # Resend requires `to` to be a list of strings
                to_list = list(msg.to) if msg.to else []
                if not to_list:
                    logger.warning("[RESEND] Skipping message with no recipients.")
                    continue

                params = {
                    "from": msg.from_email,
                    "to": to_list,
                    "subject": msg.subject,
                    "text": msg.body or " ",
                }
                if html:
                    params["html"] = html

                logger.info(f"[RESEND] Sending to {to_list} subject={msg.subject!r}")
                resend.Emails.send(params)
                sent += 1
                logger.info(f"[RESEND] Sent OK to {to_list}")

            except Exception as e:
                logger.error(f"[RESEND] Failed to send to {msg.to}: {e}", exc_info=True)
                if not self.fail_silently:
                    raise

        return sent
