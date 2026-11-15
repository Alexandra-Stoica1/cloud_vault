from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TierId(StrEnum):
    """Ids of the seeded tiers. Tiers are rows (not a CHECK), so new ones can be added as data."""

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


class Tier(Base):
    """Subscription plan (reference data): free / standard / premium."""

    __tablename__ = "tiers"
    __table_args__ = (
        CheckConstraint("storage_limit_bytes > 0", name="storage_limit_positive"),
        CheckConstraint("max_file_size_bytes > 0", name="max_file_size_positive"),
        CheckConstraint("price_ron >= 0", name="price_non_negative"),
        # NULL = unlimited, 0 = no shared buckets allowed.
        CheckConstraint("max_shared_buckets IS NULL OR max_shared_buckets >= 0",
                        name="max_shared_buckets_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    storage_limit_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_ron: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_shared_buckets: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(back_populates="tier_ref")
