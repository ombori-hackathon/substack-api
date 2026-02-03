from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.reminder_log import ReminderLog
from app.models.user import User
from app.schemas.reminder import ReminderLogListResponse, ReminderLogResponse

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=ReminderLogListResponse)
async def get_reminder_history(
    limit: int = Query(default=50, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the reminder history for the current user."""
    query = db.query(ReminderLog).filter(ReminderLog.user_id == current_user.id)

    total_count = query.count()

    reminders = (
        query.order_by(desc(ReminderLog.sent_at)).offset(offset).limit(limit).all()
    )

    return ReminderLogListResponse(
        items=[ReminderLogResponse.model_validate(r) for r in reminders],
        total_count=total_count,
        offset=offset,
        limit=limit,
    )
