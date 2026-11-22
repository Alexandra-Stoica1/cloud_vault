import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import TierId


class UserViewModel(BaseModel):
    """User data shown in the views and re-rendered in the forms after a validation error."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    username: str = ""
    email: str = ""
    bio: str | None = None
    tier: str = TierId.FREE
    email_verified: bool = False
    is_admin: bool = False
    created_at: datetime | None = None
