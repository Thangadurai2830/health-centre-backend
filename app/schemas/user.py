import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole, UserStatus


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mobile_number: str
    country_code: str
    full_name: str | None
    email: str | None
    language: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    profile_completion_percent: int
    created_at: datetime
    last_login: datetime | None


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    language: str | None = None
