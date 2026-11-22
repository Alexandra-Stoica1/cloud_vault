from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tier


class TierRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> Sequence[Tier]:
        return self.session.scalars(select(Tier).order_by(Tier.price_ron)).all()

    def get_by_id(self, tier_id: str) -> Tier | None:
        return self.session.get(Tier, tier_id)

    def add(
        self,
        tier_id: str,
        storage_limit_bytes: int,
        price_ron: Decimal,
        max_file_size_bytes: int,
        max_shared_buckets: int | None = None,
        description: str | None = None,
    ) -> Tier:
        tier = Tier(
            id=tier_id,
            storage_limit_bytes=storage_limit_bytes,
            price_ron=price_ron,
            max_file_size_bytes=max_file_size_bytes,
            max_shared_buckets=max_shared_buckets,
            description=description,
        )
        self.session.add(tier)
        self.session.flush()
        return tier

    def delete(self, tier: Tier) -> None:
        self.session.delete(tier)
        self.session.flush()
