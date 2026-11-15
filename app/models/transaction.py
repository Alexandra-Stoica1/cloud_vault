import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, sql_in


class TransactionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Transaction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Payment for a tier."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(sql_in("status", TransactionStatus), name="status_valid"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'RON'")
    )  # ISO 4217
    tier_purchased: Mapped[str] = mapped_column(
        String(20), ForeignKey("tiers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text(f"'{TransactionStatus.PENDING.value}'"),
    )
