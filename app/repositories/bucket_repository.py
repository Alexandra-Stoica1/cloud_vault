import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, contains_eager, selectinload

from app.models import Bucket, BucketMember, BucketRole, File, Folder, User


class BucketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _select_with_relations(self):
        """Buckets with their owner and members. Buckets of soft-deleted users are
        left out, also for the members of their shared buckets."""
        return (
            select(Bucket)
            .join(Bucket.owner)
            .where(User.deleted_at.is_(None))
            .options(contains_eager(Bucket.owner), selectinload(Bucket.members))
        )

    def get_all(self) -> Sequence[Bucket]:
        stmt = self._select_with_relations().order_by(Bucket.name)
        return self.session.scalars(stmt).all()

    def get_by_id(self, bucket_id: uuid.UUID) -> Bucket | None:
        stmt = self._select_with_relations().where(Bucket.id == bucket_id)
        return self.session.scalar(stmt)

    def get_by_owner(self, owner_id: uuid.UUID) -> Sequence[Bucket]:
        stmt = select(Bucket).where(Bucket.owner_id == owner_id).order_by(Bucket.name)
        return self.session.scalars(stmt).all()

    def get_by_owner_and_name(self, owner_id: uuid.UUID, name: str) -> Bucket | None:
        stmt = select(Bucket).where(Bucket.owner_id == owner_id, Bucket.name == name)
        return self.session.scalar(stmt)

    def get_accessible_by_user(self, user_id: uuid.UUID) -> Sequence[Bucket]:
        """Buckets the user owns or is a member of."""
        is_member = (
            select(BucketMember.bucket_id)
            .where(BucketMember.user_id == user_id)
            .scalar_subquery()
        )
        stmt = (
            self._select_with_relations()
            .where(or_(Bucket.owner_id == user_id, Bucket.id.in_(is_member)))
            .order_by(Bucket.name)
        )
        return self.session.scalars(stmt).all()

    def count_shared_by_owner(self, owner_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Bucket)
            .where(Bucket.owner_id == owner_id, Bucket.is_shared.is_(True))
        )
        return self.session.scalar(stmt) or 0

    def count_contents(self, bucket_id: uuid.UUID) -> tuple[int, int]:
        """Number of folders and files stored in the bucket."""
        folders = select(func.count()).where(Folder.bucket_id == bucket_id)
        files = select(func.count()).where(File.bucket_id == bucket_id)
        return self.session.scalar(folders) or 0, self.session.scalar(files) or 0

    def used_bytes_by_owner(self, owner_id: uuid.UUID) -> int:
        """Storage counted toward the owner's quota: the sum over their personal buckets."""
        stmt = select(func.coalesce(func.sum(Bucket.used_bytes), 0)).where(
            Bucket.owner_id == owner_id, Bucket.is_shared.is_(False)
        )
        return self.session.scalar(stmt) or 0

    def add_used_bytes(self, bucket_id: uuid.UUID, size_bytes: int) -> None:
        """Atomic increment in SQL: concurrent uploads cannot overwrite each other."""
        self.session.execute(
            update(Bucket)
            .where(Bucket.id == bucket_id)
            .values(used_bytes=Bucket.used_bytes + size_bytes)
        )

    def add(
        self,
        name: str,
        owner_id: uuid.UUID,
        description: str | None = None,
        is_shared: bool = False,
    ) -> Bucket:
        bucket = Bucket(
            name=name, owner_id=owner_id, description=description, is_shared=is_shared
        )
        if is_shared:
            # The owner of a shared bucket is also its first member.
            bucket.members.append(BucketMember(user_id=owner_id, role=BucketRole.OWNER))
        self.session.add(bucket)
        self.session.flush()
        return bucket

    def update(self, bucket: Bucket, name: str, description: str | None) -> Bucket:
        bucket.name = name
        bucket.description = description
        # updated_at is refreshed automatically (onupdate in UpdatedAtMixin).
        self.session.flush()
        return bucket

    def delete(self, bucket: Bucket) -> None:
        self.session.delete(bucket)
        self.session.flush()
