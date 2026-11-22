"""add is_admin to users

Revision ID: d49da8d8241e
Revises: 26da9bef541a
Create Date: 2026-11-22 13:38:32.412675+00:00

"""

import hashlib
import secrets
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d49da8d8241e"
down_revision: str | Sequence[str] | None = "26da9bef541a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Demo administrator. Same password as the other demo accounts (see the seed_data revision).
ADMIN = uuid.UUID("00000000-0000-4000-8000-000000000004")
ADMIN_PASSWORD = "CloudVault-demo-2026"


def hash_password(password: str) -> str:
    """Same format as app.core.security.hash_password (copied so the migration never changes)."""
    iterations = 600_000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


users_table = sa.table(
    "users",
    sa.column("id", UUID),
    sa.column("email", sa.String),
    sa.column("password_hash", sa.String),
    sa.column("username", sa.String),
    sa.column("email_verified", sa.Boolean),
    sa.column("is_admin", sa.Boolean),
    sa.column("tier", sa.String),
    sa.column("referral_code", sa.String),
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "id": ADMIN,
                "email": "admin@example.com",
                "password_hash": hash_password(ADMIN_PASSWORD),
                "username": "admin_cv",
                "email_verified": True,
                "is_admin": True,
                "tier": "free",
                "referral_code": "ADMIN2026",
            }
        ],
    )
    # 1:1 rows every user must have.
    for table in ("points_accounts", "login_streaks", "user_settings"):
        op.bulk_insert(
            sa.table(table, sa.column("user_id", UUID)), [{"user_id": ADMIN}]
        )


def downgrade() -> None:
    # The 1:1 rows are removed by ON DELETE CASCADE.
    op.execute(users_table.delete().where(users_table.c.id == ADMIN))
    op.drop_column("users", "is_admin")
