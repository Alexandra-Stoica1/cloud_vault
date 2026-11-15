from enum import StrEnum

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, sql_in


class BonusFrequency(StrEnum):
    ONCE = "once"
    PER_ACTION = "per_action"
    DAILY = "daily"
    PER_THRESHOLD = "per_threshold"


class BonusRule(Base):
    """Reference data: an action that grants points (id = bonus_events.event_type)."""

    __tablename__ = "bonus_rules"
    __table_args__ = (
        CheckConstraint(sql_in("frequency", BonusFrequency), name="frequency_valid"),
        CheckConstraint("points > 0", name="points_positive"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_notes: Mapped[str | None] = mapped_column(String(500))
