import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, computed_field

from app.core.formatting import format_size
from app.models import Bucket

# JSON API (/api/buckets)


class BucketCreate(BaseModel):
    """POST body. The owner is the authenticated user, so it is not sent."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_shared: bool = False


class BucketUpdate(BaseModel):
    """PUT body: the full set of editable fields. Owner and shared flag are fixed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class BucketOwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    tier: str


class BucketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_shared: bool
    used_bytes: int
    owner: BucketOwnerResponse
    member_count: Annotated[int, BeforeValidator(len)] = Field(
        validation_alias="members"
    )
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def used_size(self) -> str:
        return format_size(self.used_bytes)


# HTML views (/buckets)


class BucketViewModel(BaseModel):
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
