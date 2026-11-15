import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class PointsRedemption(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit trail of spent points."""

    __tablename__ = "points_redemptions"
    __table_args__ = (
        CheckConstraint("points_spent > 0", name="points_spent_positive"),
        Index(None, "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(50), ForeignKey("redemption_rules.id"), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = permanent
