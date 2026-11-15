from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RedemptionRule(Base):
    """Reference data: a reward bought with points (id = points_redemptions.reward_type)."""

    __tablename__ = "redemption_rules"
    __table_args__ = (
        CheckConstraint("cost_points > 0", name="cost_points_positive"),
        # NULL = permanent benefit.
        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0", name="duration_days_positive"
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_points: Mapped[int] = mapped_column(Integer, nullable=False)
    benefit_description: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer)
