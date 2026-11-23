import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models import Bucket, File, User


class FileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _select_with_relations(self):
        """Files with their bucket, folder and uploader. Files in the buckets of
        soft-deleted users are left out, like the buckets themselves."""
        return (
            select(File)
            .join(File.bucket)
            .join(Bucket.owner)
            .where(User.deleted_at.is_(None))
            .options(
                contains_eager(File.bucket).contains_eager(Bucket.owner),
                joinedload(File.folder),
                joinedload(File.uploader),
            )
        )

    def get_all(self) -> Sequence[File]:
        stmt = self._select_with_relations().order_by(File.filename)
        return self.session.scalars(stmt).all()

    def get_by_id(self, file_id: uuid.UUID) -> File | None:
        stmt = self._select_with_relations().where(File.id == file_id)
        return self.session.scalar(stmt)

    def add(
        self,
        file_id: uuid.UUID,
        file_key: str,
        filename: str,
        size_bytes: int,
        bucket_id: uuid.UUID,
        uploader_id: uuid.UUID,
        mime_type: str | None = None,
        folder_id: uuid.UUID | None = None,
        is_public: bool = False,
    ) -> File:
        file = File(
            id=file_id,
            file_key=file_key,
            filename=filename,
            size_bytes=size_bytes,
            bucket_id=bucket_id,
            uploader_id=uploader_id,
            mime_type=mime_type,
            folder_id=folder_id,
            is_public=is_public,
        )
        self.session.add(file)
        self.session.flush()
        return file

    def update(
        self,
        file: File,
        filename: str,
        folder_id: uuid.UUID | None,
        is_public: bool,
    ) -> File:
        file.filename = filename
        file.folder_id = folder_id
        file.is_public = is_public
        self.session.flush()
        return file
