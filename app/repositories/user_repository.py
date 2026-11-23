import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LoginStreak, PointsAccount, User, UserSettings


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _active():
        """Every read goes through here, so soft-deleted users are never returned."""
        return select(User).where(User.deleted_at.is_(None))

    def get_all(self) -> Sequence[User]:
        return self.session.scalars(self._active().order_by(User.username)).all()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.scalar(self._active().where(User.id == user_id))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(self._active().where(User.email == email))

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(self._active().where(User.username == username))

    def add(
        self,
        email: str,
        username: str,
        password_hash: str,
        tier: str,
        referral_code: str,
        bio: str | None = None,
        email_verified: bool = False,
    ) -> User:
        """Add a user together with the 1:1 rows every user must have."""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            tier=tier,
            bio=bio,
            email_verified=email_verified,
            referral_code=referral_code,
        )
        user.points_account = PointsAccount()
        user.login_streak = LoginStreak()
        user.settings = UserSettings()
        self.session.add(user)
        self.session.flush()
        return user

    def update(
        self,
        user: User,
        email: str,
        username: str,
        tier: str,
        bio: str | None,
        email_verified: bool,
    ) -> User:
        user.email = email
        user.username = username
        user.tier = tier
        user.bio = bio
        user.email_verified = email_verified
        self.session.flush()
        return user

    def soft_delete(self, user: User) -> None:
        """Mark the user as deleted. The row and everything linked to it are kept."""
        user.deleted_at = func.now()
        self.session.flush()
