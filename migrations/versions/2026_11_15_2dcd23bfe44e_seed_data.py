"""seed_data

Revision ID: 2dcd23bfe44e
Revises: e4efec57ca9b
Create Date: 2026-11-15 16:40:35.561137+00:00

"""

import hashlib
import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "2dcd23bfe44e"
down_revision: str | Sequence[str] | None = "e4efec57ca9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


GB = 1024**3
MB = 1024**2

# All demo accounts use this password.
DEMO_PASSWORD = "CloudVault-demo-2026"

# Fixed ids: needed to insert the 1:1 rows below and to make the downgrade exact.
ALICE = uuid.UUID("00000000-0000-4000-8000-000000000001")
BOB = uuid.UUID("00000000-0000-4000-8000-000000000002")
CAROL = uuid.UUID("00000000-0000-4000-8000-000000000003")
DEMO_USER_IDS = [ALICE, BOB, CAROL]


def hash_password(password: str) -> str:
    """Same format as app.core.security.hash_password (copied so the migration never changes)."""
    iterations = 600_000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


tiers_table = sa.table(
    "tiers",
    sa.column("id", sa.String),
    sa.column("storage_limit_bytes", sa.BigInteger),
    sa.column("price_ron", sa.Numeric),
    sa.column("max_file_size_bytes", sa.BigInteger),
    sa.column("max_shared_buckets", sa.Integer),
    sa.column("description", sa.Text),
)

users_table = sa.table(
    "users",
    sa.column("id", UUID),
    sa.column("email", sa.String),
    sa.column("password_hash", sa.String),
    sa.column("username", sa.String),
    sa.column("email_verified", sa.Boolean),
    sa.column("tier", sa.String),
    sa.column("referral_code", sa.String),
)

points_accounts_table = sa.table("points_accounts", sa.column("user_id", UUID))
login_streaks_table = sa.table("login_streaks", sa.column("user_id", UUID))
user_settings_table = sa.table("user_settings", sa.column("user_id", UUID))

buckets_table = sa.table(
    "buckets",
    sa.column("owner_id", UUID),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)

subscriptions_table = sa.table(
    "subscriptions",
    sa.column("user_id", UUID),
    sa.column("tier", sa.String),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("expires_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        tiers_table,
        [
            {
                "id": "free",
                "storage_limit_bytes": 5 * GB,
                "price_ron": 0,
                "max_file_size_bytes": 500 * MB,
                "max_shared_buckets": 0,
                "description": "Free plan: 5 GB storage, no shared buckets.",
            },
            {
                "id": "standard",
                "storage_limit_bytes": 50 * GB,
                "price_ron": 15,
                "max_file_size_bytes": 2 * GB,
                "max_shared_buckets": 2,
                "description": "Standard plan: 50 GB storage, up to 2 shared buckets.",
            },
            {
                "id": "premium",
                "storage_limit_bytes": 200 * GB,
                "price_ron": 35,
                "max_file_size_bytes": 10 * GB,
                "max_shared_buckets": 10,
                "description": "Premium plan: 200 GB storage, up to 10 shared buckets.",
            },
        ],
    )

    password_hash = hash_password(DEMO_PASSWORD)
    op.bulk_insert(
        users_table,
        [
            {
                "id": ALICE,
                "email": "alice@example.com",
                "password_hash": password_hash,
                "username": "alice_cv",
                "email_verified": True,
                "tier": "standard",
                "referral_code": "ALICE2026",
            },
            {
                "id": BOB,
                "email": "bob@example.com",
                "password_hash": password_hash,
                "username": "bob_cv",
                "email_verified": False,
                "tier": "free",
                "referral_code": "BOB2026",
            },
            {
                "id": CAROL,
                "email": "carol@example.com",
                "password_hash": password_hash,
                "username": "carol_cv",
                "email_verified": True,
                "tier": "premium",
                "referral_code": "CAROL2026",
            },
        ],
    )

    # 1:1 rows every user must have.
    one_row_per_user = [{"user_id": user_id} for user_id in DEMO_USER_IDS]
    op.bulk_insert(points_accounts_table, one_row_per_user)
    op.bulk_insert(login_streaks_table, one_row_per_user)
    op.bulk_insert(user_settings_table, one_row_per_user)

    # One personal bucket per user.
    op.bulk_insert(
        buckets_table,
        [
            {
                "owner_id": user_id,
                "name": "Personal",
                "description": "Default personal bucket",
            }
            for user_id in DEMO_USER_IDS
        ],
    )

    # Paid tiers need an active subscription, so users.tier matches subscriptions.
    now = datetime.now(UTC)
    op.bulk_insert(
        subscriptions_table,
        [
            {
                "user_id": ALICE,
                "tier": "standard",
                "started_at": now,
                "expires_at": now + timedelta(days=30),
            },
            {
                "user_id": CAROL,
                "tier": "premium",
                "started_at": now,
                "expires_at": now + timedelta(days=30),
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Points accounts, streaks, settings, buckets and subscriptions are removed by ON DELETE CASCADE.
    op.execute(users_table.delete().where(users_table.c.id.in_(DEMO_USER_IDS)))
    op.execute(
        tiers_table.delete().where(
            tiers_table.c.id.in_(["free", "standard", "premium"])
        )
    )
