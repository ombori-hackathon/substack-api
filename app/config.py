from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5433/hackathon"
    debug: bool = True

    # JWT settings
    secret_key: str = "hackathon-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Email settings (Resend)
    resend_api_key: Optional[str] = None
    email_from_address: str = "SubStack <reminders@yourdomain.com>"

    # Scheduler settings
    enable_scheduler: bool = True
    reminder_check_hour: int = 9  # Hour in UTC to run daily reminder check

    class Config:
        env_file = ".env"


settings = Settings()
