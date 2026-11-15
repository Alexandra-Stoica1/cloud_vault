import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class LoginStreak(Base):
    """Consecutive login days (1:1 with users)."""

    __tablename__ = "login_streaks"
    __table_args__ = (
        CheckConstraint("current_streak >= 0", name="current_streak_non_negative"),
        CheckConstraint("longest_streak >= current_streak", name="longest_ge_current"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    current_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_login_date: Mapped[date | None] = mapped_column(Date)
    longest_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    user: Mapped["User"] = relationship(back_populates="login_streak")
