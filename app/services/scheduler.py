import logging
from datetime import date, datetime, time, timedelta, timezone

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models.reminder_log import ReminderLog
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email import email_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def process_renewal_reminders():
    """
    Process renewal reminders for all users.
    This job runs daily and checks for subscriptions where
    days_until_renewal == reminder_days_before.
    """
    logger.info("Starting renewal reminder job")
    db: Session = SessionLocal()

    try:
        today = date.today()

        # Get all active subscriptions with their users
        subscriptions = (
            db.query(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .filter(
                Subscription.status == "active",
                Subscription.deleted_at.is_(None),
            )
            .all()
        )

        logger.info(f"Found {len(subscriptions)} active subscriptions to check")

        for subscription, user in subscriptions:
            try:
                process_subscription_reminder(db, subscription, user, today)
            except Exception as e:
                logger.error(
                    f"Error processing subscription {subscription.id}: {e}"
                )
                continue

        db.commit()
        logger.info("Renewal reminder job completed")

    except Exception as e:
        logger.error(f"Error in renewal reminder job: {e}")
        db.rollback()
    finally:
        db.close()


def process_subscription_reminder(
    db: Session,
    subscription: Subscription,
    user: User,
    today: date,
):
    """Process a single subscription for reminder."""
    days_until_renewal = (subscription.next_billing_date - today).days

    # Check if this subscription is due for a reminder
    if days_until_renewal != subscription.reminder_days_before:
        return

    # The scheduled_for datetime for this billing cycle
    scheduled_for = datetime.combine(
        subscription.next_billing_date, time.min, tzinfo=timezone.utc
    )

    # Check if we've already sent a reminder for this billing date
    existing_reminder = (
        db.query(ReminderLog)
        .filter(
            ReminderLog.subscription_id == subscription.id,
            ReminderLog.scheduled_for == scheduled_for,
        )
        .first()
    )

    if existing_reminder:
        logger.debug(
            f"Reminder already exists for subscription {subscription.id} "
            f"scheduled_for {scheduled_for}"
        )
        return

    logger.info(
        f"Processing reminder for subscription {subscription.id} "
        f"({subscription.name}) for user {user.email}"
    )

    # Always create an in_app reminder
    in_app_log = ReminderLog(
        user_id=user.id,
        subscription_id=subscription.id,
        reminder_type="in_app",
        scheduled_for=scheduled_for,
        status="sent",
    )
    db.add(in_app_log)

    # Send email if user has email notifications enabled
    if user.email_notifications_enabled:
        success, email_id, error_message = email_service.send_renewal_reminder(
            to_email=user.email,
            subscription_name=subscription.name,
            cost=subscription.cost,
            currency=subscription.currency,
            days_until_renewal=days_until_renewal,
            next_billing_date=subscription.next_billing_date.isoformat(),
        )

        email_log = ReminderLog(
            user_id=user.id,
            subscription_id=subscription.id,
            reminder_type="email",
            scheduled_for=scheduled_for,
            status="sent" if success else "failed",
            email_id=email_id,
            error_message=error_message,
        )
        db.add(email_log)
    else:
        # Log that email was skipped
        email_log = ReminderLog(
            user_id=user.id,
            subscription_id=subscription.id,
            reminder_type="email",
            scheduled_for=scheduled_for,
            status="skipped",
            error_message="User has email notifications disabled",
        )
        db.add(email_log)

    logger.info(f"Created reminder logs for subscription {subscription.id}")


def start_scheduler():
    """Start the background scheduler."""
    if not settings.enable_scheduler:
        logger.info("Scheduler is disabled via configuration")
        return

    if scheduler.running:
        logger.info("Scheduler is already running")
        return

    # Schedule the daily renewal check
    trigger = CronTrigger(
        hour=settings.reminder_check_hour,
        minute=0,
        timezone=pytz.UTC,
    )
    scheduler.add_job(
        process_renewal_reminders,
        trigger=trigger,
        id="renewal_reminders",
        name="Daily Renewal Reminder Check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Renewal check scheduled for {settings.reminder_check_hour}:00 UTC daily"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def run_reminder_job_now():
    """
    Manually trigger the reminder job (useful for testing).
    """
    logger.info("Manually triggering renewal reminder job")
    process_renewal_reminders()
