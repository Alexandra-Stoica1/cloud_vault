from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    dummy_password_hash,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import User
from app.repositories import RefreshTokenRepository, UserRepository
from app.services.exceptions import AuthenticationError, ConflictError

INVALID_CREDENTIALS = "Invalid email or password."
INVALID_REFRESH_TOKEN = "Invalid or expired refresh token."


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int  # access token lifetime, in seconds


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def register(self, email: str, username: str, password: str) -> User:
        email = email.lower()
        if self.users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists.")
        if self.users.get_by_username(username) is not None:
            raise ConflictError("A user with this username already exists.")
        try:
            return self.users.create(
                email=email, username=username, password_hash=hash_password(password)
            )
        except IntegrityError as error:
            # Another request registered the same email / username in the meantime.
            self.session.rollback()
            raise ConflictError(
                "A user with this email or username already exists."
            ) from error

    def login(self, email: str, password: str) -> TokenPair:
        user = self.users.get_by_email(email.lower())
        # Always run one password check, so unknown e-mails are not faster to reject.
        password_hash = user.password_hash if user else dummy_password_hash()
        if not verify_password(password, password_hash) or user is None:
            raise AuthenticationError(INVALID_CREDENTIALS)
        tokens = self._issue_tokens(user)
        self.session.commit()
        return tokens

    def refresh(self, refresh_token: str) -> TokenPair:
        stored = self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if stored is None:
            raise AuthenticationError(INVALID_REFRESH_TOKEN)
        if stored.revoked:
            # A revoked token was used again: it may have been stolen. Log the user out everywhere.
            self.refresh_tokens.revoke_all_for_user(stored.user_id)
            self.session.commit()
            raise AuthenticationError(INVALID_REFRESH_TOKEN)
        if stored.expires_at <= datetime.now(UTC):
            raise AuthenticationError(INVALID_REFRESH_TOKEN)

        # Rotation: the old refresh token can no longer be used.
        self.refresh_tokens.revoke(stored)
        tokens = self._issue_tokens(stored.user)
        self.session.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token. Unknown or already revoked tokens are ignored."""
        stored = self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if stored is not None and not stored.revoked:
            self.refresh_tokens.revoke(stored)
            self.session.commit()

    def _issue_tokens(self, user: User) -> TokenPair:
        access_token, expires_in = create_access_token(user.id)
        refresh_token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            days=get_settings().refresh_token_expire_days
        )
        self.refresh_tokens.add(user.id, hash_token(refresh_token), expires_at)
        return TokenPair(access_token, refresh_token, expires_in)
