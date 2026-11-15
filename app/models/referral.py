import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Referral(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A user can be referred only once. The bonus is granted after the referred user's first upload."""

    __tablename__ = "referrals"
    __table_args__ = (CheckConstraint("referrer_id <> referred_id", name="not_self_referral"),)

    referrer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    bonus_granted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
