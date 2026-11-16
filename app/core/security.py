import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache

import jwt

from app.core.config import get_settings

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return a self-describing hash: ``pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def hash_token(token: str) -> str:
    """SHA-256 of an opaque token (refresh tokens, invitation and share links).
    Only the hash is stored; the raw token is given to the user once.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(n_bytes: int = 32) -> str:
    return secrets.token_urlsafe(n_bytes)


@cache
def dummy_password_hash() -> str:
    """A valid hash of a random password, computed once.
    Checked when the e-mail is unknown, so a failed login takes the same time whether
    or not the account exists (no user enumeration by timing).
    """
    return hash_password(secrets.token_urlsafe(16))


class InvalidAccessTokenError(Exception):
    """The access token is malformed, has a bad signature or has expired."""


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Return a signed JWT for the user and its lifetime in seconds."""
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    """Validate the JWT and return the user id it was issued for."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "type"]},
        )
        if payload["type"] != "access":
            raise InvalidAccessTokenError
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as error:
        raise InvalidAccessTokenError from error
