import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import BucketCreate, BucketResponse, BucketUpdate
from app.services import BucketService

router = APIRouter(prefix="/api/buckets", tags=["buckets API"])


@router.get("", response_model=list[BucketResponse])
def get_buckets(session: DbSession, user: CurrentUser):
    """All buckets the current user owns or is a member of."""
    buckets = BucketService(session).list_accessible(user.id)
    return [BucketResponse.model_validate(bucket) for bucket in buckets]


@router.get("/{bucket_id}", response_model=BucketResponse)
def get_bucket(bucket_id: uuid.UUID, session: DbSession, user: CurrentUser):
    """One bucket. 404 if it does not exist or the user has no access to it."""
    bucket = BucketService(session).get_accessible(bucket_id, user.id)
    return BucketResponse.model_validate(bucket)


@router.post("", response_model=BucketResponse, status_code=status.HTTP_201_CREATED)
def create_bucket(body: BucketCreate, session: DbSession, user: CurrentUser):
    """Create a bucket owned by the current user.
    409 for a duplicate name, 400 if the tier does not allow another shared bucket.
    """
    bucket = BucketService(session).create(
        owner_id=user.id,
        name=body.name,
        description=body.description,
        is_shared=body.is_shared,
    )
    return BucketResponse.model_validate(bucket)


@router.put("/{bucket_id}", response_model=BucketResponse)
def update_bucket(
    bucket_id: uuid.UUID, body: BucketUpdate, session: DbSession, user: CurrentUser
):
    """Replace name and description. Only the owner can update (403 for members)."""
    bucket = BucketService(session).update(
        bucket_id,
        name=body.name,
        description=body.description,
        acting_user_id=user.id,
    )
    return BucketResponse.model_validate(bucket)


@router.delete("/{bucket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket(bucket_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    """Delete the bucket with all its folders and files.
    Only the owner can delete (403 for members, 404 without access).
    """
    BucketService(session).delete(bucket_id, acting_user_id=user.id)
