import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Bucket, BucketMember, BucketRole


class BucketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> Sequence[Bucket]:
        stmt = select(Bucket).options(joinedload(Bucket.owner)).order_by(Bucket.name)
        return self.session.scalars(stmt).all()

    def get_by_id(self, bucket_id: uuid.UUID) -> Bucket | None:
        stmt = select(Bucket).options(joinedload(Bucket.owner)).where(Bucket.id == bucket_id)
        return self.session.scalar(stmt)

    def get_by_owner(self, owner_id: uuid.UUID) -> Sequence[Bucket]:
        stmt = select(Bucket).where(Bucket.owner_id == owner_id).order_by(Bucket.name)
        return self.session.scalars(stmt).all()

    def create(
        self,
        name: str,
        owner_id: uuid.UUID,
        description: str | None = None,
        is_shared: bool = False,
    ) -> Bucket:
        bucket = Bucket(name=name, owner_id=owner_id, description=description, is_shared=is_shared)
        if is_shared:
            # The owner of a shared bucket is also its first member.
            bucket.members.append(BucketMember(user_id=owner_id, role=BucketRole.OWNER))
        self.session.add(bucket)
        self.session.commit()
        self.session.refresh(bucket)
        return bucket

    def update(
        self,
        bucket_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Bucket | None:
        bucket = self.get_by_id(bucket_id)
        if bucket is None:
            return None
        if name is not None:
            bucket.name = name
        if description is not None:
            bucket.description = description
        # updated_at is refreshed automatically (onupdate in UpdatedAtMixin).
        self.session.commit()
        self.session.refresh(bucket)
        return bucket

    def delete(self, bucket_id: uuid.UUID) -> bool:
        bucket = self.get_by_id(bucket_id)
        if bucket is None:
            return False
        self.session.delete(bucket)
        self.session.commit()
        return True
