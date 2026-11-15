import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Bucket


class BucketViewModel(BaseModel):
    """Bucket data shown in the views and re-rendered in the forms after a validation error."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    name: str = ""
    description: str | None = None
    is_shared: bool = False
    used_bytes: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    owner_id: uuid.UUID | None = None
    owner_username: str = ""
    owner_tier: str = ""

    @classmethod
    def from_entity(cls, bucket: Bucket) -> "BucketViewModel":
        return cls(
            id=bucket.id,
            name=bucket.name,
            description=bucket.description,
            is_shared=bucket.is_shared,
            used_bytes=bucket.used_bytes,
            created_at=bucket.created_at,
            updated_at=bucket.updated_at,
            owner_id=bucket.owner_id,
            owner_username=bucket.owner.username,
            owner_tier=bucket.owner.tier,
        )
