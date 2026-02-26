"""Gmail SMTP email sender."""
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
DISPLAY_NAME = "Rachely"


class EmailSender:
    def __init__(self):
        self.email_user = os.getenv("EMAIL_USER", "rachelyayn4734@gmail.com")
        self.email_password = os.getenv("EMAIL_APP_PASSWORD")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL", "rachelyayn@gmail.com")

    async def send(self, subject: str, html_body: str) -> bool:
        if not self.email_password:
            log.error("Missing config. Need: EMAIL_APP_PASSWORD")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{DISPLAY_NAME} <{self.email_user}>"
        msg["To"] = self.recipient_email
        msg["Reply-To"] = self.email_user
        msg["X-Mailer"] = "Rachely-Weather-Agent/1.0"

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(self.email_user, self.email_password)
                server.sendmail(self.email_user, self.recipient_email, msg.as_string())
            log.info(
                "[Gmail SMTP] Email sent | to=%s | subject='%s'",
                self.recipient_email,
                subject,
            )
            return True
        except smtplib.SMTPAuthenticationError as e:
            log.error("[Gmail SMTP] Authentication failed - check EMAIL_APP_PASSWORD: %s", e)
            return False
        except smtplib.SMTPException as e:
            log.error("[Gmail SMTP] SMTP error: %s", e)
            return False
        except Exception as e:
            log.error("[Gmail SMTP] Unexpected error sending email: %s", e)
            return False
