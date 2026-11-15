import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class BonusEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit trail of earned points."""

    __tablename__ = "bonus_events"
    __table_args__ = (
        CheckConstraint("points_earned > 0", name="points_earned_positive"),
        Index(None, "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), ForeignKey("bonus_rules.id"), nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    # "metadata" is reserved on declarative classes, hence the trailing underscore.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
