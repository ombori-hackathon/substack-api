from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReminderLogResponse(BaseModel):
    id: int
    user_id: int
    subscription_id: int
    reminder_type: str
    scheduled_for: datetime
    sent_at: datetime
    status: str
    error_message: Optional[str] = None
    email_id: Optional[str] = None

    class Config:
        from_attributes = True


class ReminderLogListResponse(BaseModel):
    items: list[ReminderLogResponse]
    total_count: int
    offset: int
    limit: int
