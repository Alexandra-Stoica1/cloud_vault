import secrets
import uuid
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Tier, TierId, User
from app.repositories import RefreshTokenRepository, TierRepository, UserRepository
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ServiceError,
)

USER_NOT_FOUND = "User not found."
EMAIL_TAKEN = "A user with this email already exists."
USERNAME_TAKEN = "A user with this username already exists."
TIER_NOT_FOUND = "The selected tier does not exist."
CANNOT_DELETE_SELF = "You cannot delete your own account."

# Database constraint name -> error raised when a concurrent request wins the race.
CONSTRAINT_ERRORS: dict[str, tuple[type[ServiceError], str]] = {
    "uq_users_email": (ConflictError, EMAIL_TAKEN),
    "uq_users_username": (ConflictError, USERNAME_TAKEN),
    "uq_users_referral_code": (
        ConflictError,
        "Could not generate a unique referral code. Please try again.",
    ),
    "fk_users_tier_tiers": (NotFoundError, TIER_NOT_FOUND),
}
DEFAULT_ERROR = (ConflictError, "The user could not be saved.")


def generate_referral_code() -> str:
    return secrets.token_hex(4).upper()


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tiers = TierRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def list_all(self) -> Sequence[User]:
        return self.users.get_all()

    def list_tiers(self) -> Sequence[Tier]:
        return self.tiers.get_all()

    def get(self, user_id: uuid.UUID) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(USER_NOT_FOUND)
        return user

    def create(
        self,
        email: str,
        username: str,
        password: str,
        tier: str = TierId.FREE,
        bio: str | None = None,
        email_verified: bool = False,
    ) -> User:
        """Create a user with a unique referral code and the 1:1 rows every user needs."""
        email = email.lower()  # login looks e-mails up in lower case
        self._check_unique(email, username)
        self._check_tier(tier)

        try:
            user = self.users.add(
                email=email,
                username=username,
                password_hash=hash_password(password),
                tier=tier,
                bio=bio,
                email_verified=email_verified,
                referral_code=generate_referral_code(),
            )
            self.session.commit()
        except IntegrityError as error:
            self._raise_integrity_error(error)
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
    ) -> User:
        user = self.get(user_id)
        email = email.lower()
        self._check_unique(email, username, exclude_id=user.id)
        self._check_tier(tier)

        try:
            self.users.update(
                user,
                email=email,
                username=username,
                tier=tier,
                bio=bio,
                email_verified=email_verified,
            )
            self.session.commit()
        except IntegrityError as error:
            self._raise_integrity_error(error)
        self.session.refresh(user)
        return user

    def delete(
        self, user_id: uuid.UUID, acting_user_id: uuid.UUID | None = None
    ) -> None:
        """Soft delete: the account disappears from the application and is signed out
        everywhere, but its row and history (payments, points, ...) are kept.

        `acting_user_id` is the admin doing the delete, who cannot delete themselves.
        """
        user = self.get(user_id)  # 404 if it does not exist or is already deleted
        if acting_user_id is not None and user.id == acting_user_id:
            raise BusinessRuleError(CANNOT_DELETE_SELF)

        self.users.soft_delete(user)
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.session.commit()

    def _check_unique(
        self, email: str, username: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        existing = self.users.get_by_email(email)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(EMAIL_TAKEN)
        existing = self.users.get_by_username(username)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(USERNAME_TAKEN)

    def _check_tier(self, tier: str) -> None:
        if self.tiers.get_by_id(tier) is None:
            raise NotFoundError(TIER_NOT_FOUND)

    def _raise_integrity_error(self, error: IntegrityError) -> NoReturn:
        """Another request saved the same email / username in the meantime."""
        self.session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        error_class, message = CONSTRAINT_ERRORS.get(constraint, DEFAULT_ERROR)
        raise error_class(message) from error
