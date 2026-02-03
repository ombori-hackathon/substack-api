from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL = system category
    name = Column(String(50), nullable=False)
    icon = Column(String(50), nullable=False, default="folder")  # SF Symbol name
    color = Column(String(7), nullable=False, default="#808080")  # Hex code
    is_system = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete


# System categories to be seeded
SYSTEM_CATEGORIES = [
    {"name": "Entertainment", "icon": "play.tv.fill", "color": "#E91E63", "display_order": 1},
    {"name": "Productivity", "icon": "laptopcomputer", "color": "#2196F3", "display_order": 2},
    {"name": "Health", "icon": "heart.fill", "color": "#4CAF50", "display_order": 3},
    {"name": "Finance", "icon": "creditcard.fill", "color": "#FF9800", "display_order": 4},
    {"name": "Education", "icon": "book.fill", "color": "#9C27B0", "display_order": 5},
    {"name": "Shopping", "icon": "cart.fill", "color": "#00BCD4", "display_order": 6},
    {"name": "Other", "icon": "ellipsis.circle.fill", "color": "#607D8B", "display_order": 99},
]
