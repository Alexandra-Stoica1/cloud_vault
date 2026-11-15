import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(UpdatedAtMixin, Base):
    """Per-user preferences (1:1 with users)."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    dedup_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    notification_prefs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    user: Mapped["User"] = relationship(back_populates="settings")
