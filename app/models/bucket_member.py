import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, sql_in

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.user import User


class BucketRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class BucketMember(Base):
    """Membership in a shared bucket. The owner also gets a row with role = 'owner'."""

    __tablename__ = "bucket_members"
    __table_args__ = (CheckConstraint(sql_in("role", BucketRole), name="role_valid"),)

    bucket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    bucket: Mapped["Bucket"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
