import secrets
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LoginStreak, PointsAccount, TierId, User, UserSettings


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> Sequence[User]:
        return self.session.scalars(select(User).order_by(User.username)).all()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def create(
        self,
        email: str,
        username: str,
        password_hash: str,
        tier: str = TierId.FREE,
        bio: str | None = None,
        email_verified: bool = False,
        referral_code: str | None = None,
    ) -> User:
        """Create a user together with the 1:1 rows every user must have."""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            tier=tier,
            bio=bio,
            email_verified=email_verified,
            referral_code=referral_code or secrets.token_hex(4).upper(),
        )
        user.points_account = PointsAccount()
        user.login_streak = LoginStreak()
        user.settings = UserSettings()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(
        self,
        user_id: uuid.UUID,
        email: str,
        username: str,
        tier: str,
        bio: str | None,
        email_verified: bool,
    ) -> User | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.email = email
        user.username = username
        user.tier = tier
        user.bio = bio
        user.email_verified = email_verified
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user_id: uuid.UUID) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        self.session.delete(user)
        self.session.commit()
        return True
