import hashlib
import hmac
import secrets

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
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


def hash_token(token: str) -> str:
    """SHA-256 of an opaque token (refresh tokens, invitation and share links).
    Only the hash is stored; the raw token is given to the user once.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(n_bytes: int = 32) -> str:
    return secrets.token_urlsafe(n_bytes)
