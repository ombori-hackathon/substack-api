import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Common SF Symbols used in iOS/macOS apps - subset for validation
VALID_SF_SYMBOLS = {
    # Media & Entertainment
    "play.tv.fill", "play.circle.fill", "film.fill", "music.note", "gamecontroller.fill",
    # Productivity
    "laptopcomputer", "desktopcomputer", "keyboard", "doc.fill", "folder.fill",
    # Health
    "heart.fill", "figure.run", "cross.fill", "pills.fill", "stethoscope",
    # Finance
    "creditcard.fill", "dollarsign.circle.fill", "banknote.fill", "chart.line.uptrend.xyaxis",
    # Education
    "book.fill", "graduationcap.fill", "pencil", "lightbulb.fill", "brain.head.profile",
    # Shopping
    "cart.fill", "bag.fill", "shippingbox.fill", "gift.fill",
    # Communication
    "message.fill", "envelope.fill", "phone.fill", "video.fill",
    # Utilities
    "gearshape.fill", "wrench.fill", "hammer.fill", "cloud.fill",
    # General
    "folder", "star.fill", "bookmark.fill", "tag.fill", "house.fill",
    "ellipsis.circle.fill", "square.grid.2x2.fill", "circle.fill",
}


def validate_sf_symbol(icon: str) -> str:
    """Validate that the icon is a known SF Symbol."""
    if icon not in VALID_SF_SYMBOLS:
        raise ValueError(f"Invalid SF Symbol: {icon}. Must be one of the allowed symbols.")
    return icon


def validate_hex_color(color: str) -> str:
    """Validate that the color is a valid hex code (#RRGGBB)."""
    if not re.match(r"^#[0-9A-Fa-f]{6}$", color):
        raise ValueError("Invalid hex color. Must be in format #RRGGBB (e.g., #FF5733)")
    return color.upper()  # Normalize to uppercase


class CategoryCreate(BaseModel):
    """Schema for creating a new custom category."""

    name: str = Field(..., min_length=1, max_length=50, description="Category name (1-50 characters)")
    icon: str = Field(..., description="SF Symbol name for the icon")
    color: str = Field(..., description="Hex color code (#RRGGBB)")

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str) -> str:
        return validate_sf_symbol(v)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        return validate_hex_color(v)


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Category name (1-50 characters)")
    icon: Optional[str] = Field(None, description="SF Symbol name for the icon")
    color: Optional[str] = Field(None, description="Hex color code (#RRGGBB)")

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_sf_symbol(v)
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_hex_color(v)
        return v


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: int
    name: str
    icon: str
    color: str
    is_system: bool
    display_order: int
    subscription_count: int = 0

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """Schema for listing categories."""

    items: list[CategoryResponse]
    total_count: int
    custom_count: int
    max_custom_allowed: int = 20


class AvailableIconsResponse(BaseModel):
    """Schema for listing available SF Symbols."""

    icons: list[str]
