from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(
        Integer, ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    reminder_type = Column(String(20), nullable=False)  # "email" or "in_app"
    scheduled_for = Column(DateTime, nullable=False)  # The renewal date
    sent_at = Column(DateTime, default=utc_now)
    status = Column(String(20), nullable=False)  # "sent", "failed", "skipped"
    error_message = Column(Text, nullable=True)
    email_id = Column(String(100), nullable=True)  # Resend tracking ID
