import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.file import File


class FileShare(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Public link to a file. The link carries the raw token; the database stores its SHA-256 hash."""

    __tablename__ = "file_shares"
    __table_args__ = (
        CheckConstraint("access_count >= 0", name="access_count_non_negative"),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # NULL = never
    access_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    file: Mapped["File"] = relationship(back_populates="shares")
