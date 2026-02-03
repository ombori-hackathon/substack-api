"""Tests for scheduler job logic."""

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestProcessRenewalReminders:
    """Tests for the process_subscription_reminder function."""

    def test_skips_subscription_not_due_for_reminder(self, auth_client, db_session):
        """Should skip subscription when days_until_renewal != reminder_days_before."""
        from app.models.reminder_log import ReminderLog
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.scheduler import process_subscription_reminder

        user = auth_client.test_user
        today = date.today()

        # Create subscription renewing in 10 days with 3-day reminder
        subscription = Subscription(
            user_id=user.id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=today + timedelta(days=10),
            reminder_days_before=3,
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        # Process reminder (should skip)
        process_subscription_reminder(db_session, subscription, user, today)
        db_session.commit()

        # Should not create any reminder logs
        logs = db_session.query(ReminderLog).filter(
            ReminderLog.subscription_id == subscription.id
        ).all()
        assert len(logs) == 0

    def test_sends_reminder_when_due(self, auth_client, db_session):
        """Should create reminder logs when days_until_renewal == reminder_days_before."""
        from app.models.reminder_log import ReminderLog
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.scheduler import process_subscription_reminder

        user = auth_client.test_user
        today = date.today()

        # Create subscription renewing in 3 days with 3-day reminder
        subscription = Subscription(
            user_id=user.id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=today + timedelta(days=3),
            reminder_days_before=3,
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        # Process reminder
        with patch("app.services.scheduler.email_service") as mock_email:
            mock_email.send_renewal_reminder.return_value = (True, "email-123", None)
            process_subscription_reminder(db_session, subscription, user, today)
            db_session.commit()

        # Should create in_app and email reminder logs
        logs = db_session.query(ReminderLog).filter(
            ReminderLog.subscription_id == subscription.id
        ).all()
        assert len(logs) == 2

        log_types = [log.reminder_type for log in logs]
        assert "in_app" in log_types
        assert "email" in log_types

    def test_skips_already_reminded(self, auth_client, db_session):
        """Should skip if reminder was already sent for this billing date."""
        from app.models.reminder_log import ReminderLog
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.scheduler import process_subscription_reminder

        user = auth_client.test_user
        today = date.today()
        renewal_date = today + timedelta(days=3)

        # Create subscription
        subscription = Subscription(
            user_id=user.id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=renewal_date,
            reminder_days_before=3,
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        # Create existing reminder log for this billing date
        existing_log = ReminderLog(
            user_id=user.id,
            subscription_id=subscription.id,
            reminder_type="in_app",
            scheduled_for=datetime.combine(renewal_date, time.min, tzinfo=timezone.utc),
            status="sent",
        )
        db_session.add(existing_log)
        db_session.commit()

        # Process reminder (should skip due to existing log)
        with patch("app.services.scheduler.email_service") as mock_email:
            process_subscription_reminder(db_session, subscription, user, today)
            db_session.commit()
            mock_email.send_renewal_reminder.assert_not_called()

        # Should still only have the one original log
        logs = db_session.query(ReminderLog).filter(
            ReminderLog.subscription_id == subscription.id
        ).all()
        assert len(logs) == 1

    def test_respects_email_disabled(self, auth_client, db_session):
        """Should skip email when user has email notifications disabled."""
        from app.models.reminder_log import ReminderLog
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.scheduler import process_subscription_reminder

        user = auth_client.test_user
        # Disable email notifications
        user.email_notifications_enabled = False
        db_session.commit()

        today = date.today()

        # Create subscription renewing in 3 days with 3-day reminder
        subscription = Subscription(
            user_id=user.id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=today + timedelta(days=3),
            reminder_days_before=3,
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        # Process reminder
        with patch("app.services.scheduler.email_service") as mock_email:
            process_subscription_reminder(db_session, subscription, user, today)
            db_session.commit()
            mock_email.send_renewal_reminder.assert_not_called()

        # Should create in_app log and skipped email log
        logs = db_session.query(ReminderLog).filter(
            ReminderLog.subscription_id == subscription.id
        ).all()
        assert len(logs) == 2

        email_log = next(log for log in logs if log.reminder_type == "email")
        assert email_log.status == "skipped"
        assert "disabled" in email_log.error_message.lower()

    def test_logs_failed_email(self, auth_client, db_session):
        """Should log failed email attempt."""
        from app.models.reminder_log import ReminderLog
        from app.models.subscription import Subscription
        from app.models.user import User
        from app.services.scheduler import process_subscription_reminder

        user = auth_client.test_user
        today = date.today()

        # Create subscription
        subscription = Subscription(
            user_id=user.id,
            name="Netflix",
            cost=15.99,
            currency="USD",
            billing_cycle="monthly",
            next_billing_date=today + timedelta(days=3),
            reminder_days_before=3,
        )
        db_session.add(subscription)
        db_session.commit()
        db_session.refresh(subscription)

        # Mock email service to fail
        with patch("app.services.scheduler.email_service") as mock_email:
            mock_email.send_renewal_reminder.return_value = (False, None, "SMTP error")
            process_subscription_reminder(db_session, subscription, user, today)
            db_session.commit()

        # Should have failed email log
        email_log = db_session.query(ReminderLog).filter(
            ReminderLog.subscription_id == subscription.id,
            ReminderLog.reminder_type == "email",
        ).first()
        assert email_log.status == "failed"
        assert email_log.error_message == "SMTP error"


class TestEmailService:
    """Tests for the email service."""

    def test_dry_run_when_no_api_key(self):
        """Should return success with dry-run ID when no API key configured."""
        from app.services.email import EmailService

        with patch("app.config.settings") as mock_settings:
            mock_settings.resend_api_key = None
            service = EmailService()

            success, email_id, error = service.send_renewal_reminder(
                to_email="test@example.com",
                subscription_name="Netflix",
                cost=15.99,
                currency="USD",
                days_until_renewal=3,
                next_billing_date="2026-02-10",
            )

            assert success is True
            assert email_id == "dry-run-id"
            assert error is None
