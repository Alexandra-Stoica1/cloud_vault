from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    ADMIN_SESSION_TOKEN,
    create_access_token,
    dummy_password_hash,
    generate_token,
    hash_token,
    verify_password,
)
from app.models import User
from app.repositories import RefreshTokenRepository, UserRepository
from app.services.exceptions import AuthenticationError, PermissionDeniedError
from app.services.user_service import UserService

INVALID_CREDENTIALS = "Invalid email or password."
INVALID_REFRESH_TOKEN = "Invalid or expired refresh token."
NOT_AN_ADMIN = "This account is not an administrator."


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
        """Create a free account. Raises ConflictError if the email or username is taken."""
        return UserService(self.session).create(email, username, password)

    def login(self, email: str, password: str) -> TokenPair:
        user = self._authenticate(email, password)
        tokens = self._issue_tokens(user)
        self.session.commit()
        return tokens

    def admin_login(self, email: str, password: str) -> tuple[str, int]:
        """Check an administrator's credentials and return a session token for the
        HTML pages and its lifetime in seconds.
        """
        user = self._authenticate(email, password)
        if not user.is_admin:
            raise PermissionDeniedError(NOT_AN_ADMIN)
        return create_access_token(
            user.id,
            token_type=ADMIN_SESSION_TOKEN,
            expires_in=get_settings().admin_session_expire_minutes * 60,
        )

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
        if stored.user.is_deleted:
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

    def _authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email.lower())
        # Always run one password check, so unknown e-mails are not faster to reject.
        password_hash = user.password_hash if user else dummy_password_hash()
        if not verify_password(password, password_hash) or user is None:
            raise AuthenticationError(INVALID_CREDENTIALS)
        return user

    def _issue_tokens(self, user: User) -> TokenPair:
        access_token, expires_in = create_access_token(user.id)
        refresh_token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(
            days=get_settings().refresh_token_expire_days
        )
        self.refresh_tokens.add(user.id, hash_token(refresh_token), expires_at)
        return TokenPair(access_token, refresh_token, expires_in)
