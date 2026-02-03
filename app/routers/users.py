from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UserProfileResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile including notification preferences."""
    return current_user


@router.patch("/me/notifications", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the current user's notification preferences."""
    update_data = preferences.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return NotificationPreferencesResponse(
        email_notifications_enabled=current_user.email_notifications_enabled,
        push_notifications_enabled=current_user.push_notifications_enabled,
        timezone=current_user.timezone,
    )
