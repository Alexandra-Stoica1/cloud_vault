import uuid
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Bucket
from app.repositories import BucketRepository, UserRepository
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)

BUCKET_NOT_FOUND = "Bucket not found."
DUPLICATE_NAME = "This owner already has a bucket with this name."


class BucketService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.buckets = BucketRepository(session)
        self.users = UserRepository(session)

    def list_all(self) -> Sequence[Bucket]:
        return self.buckets.get_all()

    def list_accessible(self, user_id: uuid.UUID) -> Sequence[Bucket]:
        """Buckets the user owns or is a member of."""
        return self.buckets.get_accessible_by_user(user_id)

    def get(self, bucket_id: uuid.UUID) -> Bucket:
        bucket = self.buckets.get_by_id(bucket_id)
        if bucket is None:
            raise NotFoundError(BUCKET_NOT_FOUND)
        return bucket

    def get_accessible(self, bucket_id: uuid.UUID, user_id: uuid.UUID) -> Bucket:
        bucket = self.get(bucket_id)
        if not self._can_access(bucket, user_id):
            raise NotFoundError(BUCKET_NOT_FOUND)
        return bucket

    def create(
        self,
        owner_id: uuid.UUID,
        name: str,
        description: str | None = None,
        is_shared: bool = False,
    ) -> Bucket:
        owner = self.users.get_by_id(owner_id)
        if owner is None:
            raise NotFoundError("The selected owner does not exist.")
        if self.buckets.get_by_owner_and_name(owner_id, name) is not None:
            raise ConflictError(DUPLICATE_NAME)
        if is_shared:
            self._check_shared_bucket_limit(
                owner_id, owner.tier, owner.tier_ref.max_shared_buckets
            )

        try:
            bucket = self.buckets.add(
                name=name,
                owner_id=owner_id,
                description=description,
                is_shared=is_shared,
            )
            self.session.commit()
        except IntegrityError as error:
            self._raise_duplicate_name(error)
        self.session.refresh(bucket)
        return bucket

    def update(
        self,
        bucket_id: uuid.UUID,
        name: str,
        description: str | None,
        acting_user_id: uuid.UUID | None = None,
    ) -> Bucket:
        """Change name and description. Owner and shared flag are fixed after creation."""
        bucket = self.get(bucket_id)
        if acting_user_id is not None:
            if not self._can_access(bucket, acting_user_id):
                raise NotFoundError(BUCKET_NOT_FOUND)
            if bucket.owner_id != acting_user_id:
                raise PermissionDeniedError("Only the owner can update this bucket.")

        existing = self.buckets.get_by_owner_and_name(bucket.owner_id, name)
        if existing is not None and existing.id != bucket.id:
            raise ConflictError(DUPLICATE_NAME)

        try:
            self.buckets.update(bucket, name=name, description=description)
            self.session.commit()
        except IntegrityError as error:
            self._raise_duplicate_name(error)
        self.session.refresh(bucket)
        return bucket

    @staticmethod
    def _can_access(bucket: Bucket, user_id: uuid.UUID) -> bool:
        return bucket.owner_id == user_id or any(
            member.user_id == user_id for member in bucket.members
        )

    def _check_shared_bucket_limit(
        self, owner_id: uuid.UUID, tier: str, limit: int | None
    ) -> None:
        if limit is None:  # NULL = unlimited
            return
        if self.buckets.count_shared_by_owner(owner_id) >= limit:
            if limit == 0:
                raise BusinessRuleError(
                    f"The '{tier}' tier does not allow shared buckets."
                )
            raise BusinessRuleError(
                f"The '{tier}' tier allows at most {limit} shared buckets."
            )

    def _raise_duplicate_name(self, error: IntegrityError) -> NoReturn:
        """Another request created the same bucket name in the meantime.
        The error can come from the repository flush, not only from the commit.
        """
        self.session.rollback()
        raise ConflictError(DUPLICATE_NAME) from error
