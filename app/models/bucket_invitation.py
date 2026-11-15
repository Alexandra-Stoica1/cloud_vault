import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.user import User


class BucketInvitation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Invitation to a shared bucket.

    The raw token is only sent in the e-mail link; the database stores its SHA-256 hash.
    """

    __tablename__ = "bucket_invitations"
    __table_args__ = (Index(None, "bucket_id", "invited_email"),)

    bucket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    bucket: Mapped["Bucket"] = relationship(back_populates="invitations")
    inviter: Mapped["User"] = relationship()
