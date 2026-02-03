from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Integer, String, DateTime

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Notification preferences
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    push_notifications_enabled = Column(Boolean, default=True, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
