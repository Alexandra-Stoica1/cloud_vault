import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Bucket, File


class FileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _select_with_relations(self):
        return select(File).options(
            joinedload(File.bucket).joinedload(Bucket.owner),
            joinedload(File.folder),
            joinedload(File.uploader),
        )

    def get_all(self) -> Sequence[File]:
        stmt = self._select_with_relations().order_by(File.filename)
        return self.session.scalars(stmt).all()

    def get_by_id(self, file_id: uuid.UUID) -> File | None:
        stmt = self._select_with_relations().where(File.id == file_id)
        return self.session.scalar(stmt)

    def used_bytes_by_owner(self, owner_id: uuid.UUID) -> int:
        """Storage counted toward the owner's quota: the sum over their personal buckets."""
        stmt = select(func.coalesce(func.sum(Bucket.used_bytes), 0)).where(
            Bucket.owner_id == owner_id, Bucket.is_shared.is_(False)
        )
        return self.session.scalar(stmt) or 0

    def create(
        self,
        filename: str,
        size_bytes: int,
        bucket_id: uuid.UUID,
        uploader_id: uuid.UUID,
        mime_type: str | None = None,
        folder_id: uuid.UUID | None = None,
        is_public: bool = False,
    ) -> File:
        """Save the file metadata and add its size to the bucket, in one transaction."""
        file_id = uuid.uuid4()
        file = File(
            id=file_id,
            # Object key built from ids, so files with the same name never collide.
            file_key=f"buckets/{bucket_id}/{file_id}",
            filename=filename,
            size_bytes=size_bytes,
            bucket_id=bucket_id,
            uploader_id=uploader_id,
            mime_type=mime_type,
            folder_id=folder_id,
            is_public=is_public,
        )
        self.session.add(file)
        # Atomic increment in SQL: concurrent uploads cannot overwrite each other.
        self.session.execute(
            update(Bucket)
            .where(Bucket.id == bucket_id)
            .values(used_bytes=Bucket.used_bytes + size_bytes)
        )
        self.session.commit()
        self.session.refresh(file)
        return file

    def update(
        self,
        file_id: uuid.UUID,
        filename: str,
        folder_id: uuid.UUID | None,
        is_public: bool,
    ) -> File | None:
        file = self.get_by_id(file_id)
        if file is None:
            return None
        file.filename = filename
        file.folder_id = folder_id
        file.is_public = is_public
        self.session.commit()
        self.session.refresh(file)
        return file
