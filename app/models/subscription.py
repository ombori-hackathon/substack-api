from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    cost = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    billing_cycle = Column(String(20), nullable=False)
    next_billing_date = Column(Date, nullable=False)
    category = Column(String(20), nullable=True)  # Deprecated: use category_id
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    reminder_days_before = Column(Integer, default=3)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True, default=None)

    # Cancellation fields
    status = Column(String(20), nullable=False, default="active")
    cancelled_at = Column(DateTime, nullable=True, default=None)
    cancellation_reason = Column(Text, nullable=True, default=None)
    cancellation_effective_date = Column(Date, nullable=True, default=None)
    was_free_trial = Column(Boolean, nullable=False, default=False)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True, default=None)
