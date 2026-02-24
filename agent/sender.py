"""SendGrid email sender."""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, HtmlContent,
    ReplyTo, Header, MailSettings, TrackingSettings,
    ClickTracking, OpenTracking
)

log = logging.getLogger(__name__)

DISPLAY_NAME = "Rachely"


class EmailSender:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL")

    async def send(self, subject: str, html_body: str) -> bool:
        if not all([self.api_key, self.sender_email, self.recipient_email]):
            log.error(
                "Missing config. Need: SENDGRID_API_KEY, SENDER_EMAIL, RECIPIENT_EMAIL"
            )
            return False

        message = Mail(
            from_email=Email(self.sender_email, DISPLAY_NAME),
            to_emails=To(self.recipient_email),
            subject=subject,
            html_content=HtmlContent(html_body),
        )

        # Reply-To — replies go back to the sender
        message.reply_to = ReplyTo(self.sender_email, DISPLAY_NAME)

        # List-Unsubscribe header — required by Gmail/Yahoo for bulk senders
        # prevents spam classification
        message.header = [
            Header("List-Unsubscribe", f"<mailto:{self.sender_email}?subject=unsubscribe>"),
            Header("List-Unsubscribe-Post", "List-Unsubscribe=One-Click"),
            Header("X-Mailer", "Rachely-Weather-Agent/1.0"),
            Header("Precedence", "bulk"),
        ]

        # Disable click tracking (tracked links look spammy)
        tracking = TrackingSettings()
        tracking.click_tracking = ClickTracking(enable=False, enable_text=False)
        tracking.open_tracking = OpenTracking(enable=False)
        message.tracking_settings = tracking

        try:
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            log.info(
                "[SendGrid] Email sent | status=%d | subject='%s'",
                response.status_code,
                subject,
            )
            return response.status_code in (200, 201, 202)
        except Exception as e:
            log.error("[SendGrid] Failed to send email: %s", e)
            return False
