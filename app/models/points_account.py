import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User


class PointsAccount(UpdatedAtMixin, Base):
    """Points balance (1:1 with users).

    ``balance`` is a running total and must be updated in the same DB transaction as every
    insert into bonus_events / points_redemptions. Totals earned / spent are computed from those tables.
    """

    __tablename__ = "points_accounts"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    user: Mapped["User"] = relationship(back_populates="points_account")
