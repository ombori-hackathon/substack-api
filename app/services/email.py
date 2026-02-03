import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service using Resend API."""

    def __init__(self):
        self._client = None
        if settings.resend_api_key:
            try:
                import resend

                resend.api_key = settings.resend_api_key
                self._client = resend
                logger.info("Resend email service initialized")
            except ImportError:
                logger.warning("resend package not installed")
        else:
            logger.warning("RESEND_API_KEY not configured, emails will be logged only")

    def send_renewal_reminder(
        self,
        to_email: str,
        subscription_name: str,
        cost: float,
        currency: str,
        days_until_renewal: int,
        next_billing_date: str,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Send a renewal reminder email.

        Returns:
            tuple: (success, email_id, error_message)
        """
        subject = f"Reminder: {subscription_name} renews in {days_until_renewal} day{'s' if days_until_renewal != 1 else ''}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333;">Subscription Renewal Reminder</h2>
            <p>Hi there,</p>
            <p>This is a friendly reminder that your subscription is coming up for renewal:</p>
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{subscription_name}</h3>
                <p style="margin: 5px 0;"><strong>Amount:</strong> {currency} {cost:.2f}</p>
                <p style="margin: 5px 0;"><strong>Renewal Date:</strong> {next_billing_date}</p>
                <p style="margin: 5px 0;"><strong>Days Until Renewal:</strong> {days_until_renewal}</p>
            </div>
            <p>If you wish to cancel or modify this subscription, please do so before the renewal date.</p>
            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This email was sent by SubStack, your subscription tracker.
            </p>
        </body>
        </html>
        """

        if not self._client:
            logger.info(
                f"[DRY RUN] Would send email to {to_email}: {subject}"
            )
            return True, "dry-run-id", None

        try:
            params = {
                "from": settings.email_from_address,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            response = self._client.Emails.send(params)
            email_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
            logger.info(f"Email sent to {to_email}, id: {email_id}")
            return True, email_id, None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            return False, None, error_msg


# Singleton instance
email_service = EmailService()
