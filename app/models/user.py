from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.tier import TierId

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.bucket_member import BucketMember
    from app.models.login_streak import LoginStreak
    from app.models.notification import Notification
    from app.models.points_account import PointsAccount
    from app.models.refresh_token import RefreshToken
    from app.models.subscription import Subscription
    from app.models.tier import Tier
    from app.models.user_settings import UserSettings


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Current effective tier: cache of the active subscription ('free' when there is none).
    tier: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("tiers.id"),
        nullable=False,
        server_default=text(f"'{TierId.FREE.value}'"),
        index=True,
    )
    referral_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    tier_ref: Mapped["Tier"] = relationship(back_populates="users")
    buckets: Mapped[list["Bucket"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    memberships: Mapped[list["BucketMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    points_account: Mapped["PointsAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    login_streak: Mapped["LoginStreak | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    settings: Mapped["UserSettings | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"
