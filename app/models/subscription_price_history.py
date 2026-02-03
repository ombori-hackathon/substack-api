from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class SubscriptionPriceHistory(Base):
    """Track historical price changes for subscriptions."""

    __tablename__ = "subscription_price_history"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    cost = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    billing_cycle = Column(String(20), nullable=False)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)  # NULL = current price
    created_at = Column(DateTime, default=utc_now)
