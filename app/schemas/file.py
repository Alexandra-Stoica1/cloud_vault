import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import File


class FileViewModel(BaseModel):
    """File data shown in the views and re-rendered in the forms after a validation error."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    filename: str = ""
    file_key: str = ""
    size_bytes: int = 0
    mime_type: str | None = None
    content_hash: str | None = None
    is_duplicate: bool = False
    is_public: bool = False
    created_at: datetime | None = None

    bucket_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    uploader_id: uuid.UUID | None = None

    bucket_name: str = ""
    bucket_owner_username: str = ""
    folder_name: str | None = None
    uploader_username: str | None = None

    @classmethod
    def from_entity(cls, file: File) -> "FileViewModel":
        return cls(
            id=file.id,
            filename=file.filename,
            file_key=file.file_key,
            size_bytes=file.size_bytes,
            mime_type=file.mime_type,
            content_hash=file.content_hash,
            is_duplicate=file.is_duplicate,
            is_public=file.is_public,
            created_at=file.created_at,
            bucket_id=file.bucket_id,
            folder_id=file.folder_id,
            uploader_id=file.uploader_id,
            bucket_name=file.bucket.name,
            bucket_owner_username=file.bucket.owner.username,
            folder_name=file.folder.name if file.folder else None,
            # The uploader is not always the bucket owner (shared buckets).
            # NULL when the uploader's account was deleted.
            uploader_username=file.uploader.username if file.uploader else None,
        )
