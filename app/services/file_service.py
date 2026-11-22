import uuid
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.formatting import format_size
from app.models import Bucket, File, Folder, User
from app.repositories import (
    BucketRepository,
    FileRepository,
    FolderRepository,
    UserRepository,
)
from app.services.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
    ServiceError,
)

FILE_NOT_FOUND = "File not found."
BUCKET_NOT_FOUND = "The selected bucket does not exist."
UPLOADER_NOT_FOUND = "The selected uploader does not exist."
FOLDER_NOT_FOUND = "The selected folder does not exist."
FOLDER_OUTSIDE_BUCKET = "The selected folder does not belong to this bucket."
NEGATIVE_SIZE = "The size cannot be negative."

# Database constraint name -> error raised when a check passed but the insert still failed
# (e.g. the bucket was deleted by another request in the meantime).
CONSTRAINT_ERRORS: dict[str, tuple[type[ServiceError], str]] = {
    "fk_files_bucket_id_buckets": (NotFoundError, BUCKET_NOT_FOUND),
    "fk_files_uploader_id_users": (NotFoundError, UPLOADER_NOT_FOUND),
    "fk_files_folder_id_folders": (BusinessRuleError, FOLDER_OUTSIDE_BUCKET),
    "ck_files_size_bytes_non_negative": (BusinessRuleError, NEGATIVE_SIZE),
}
DEFAULT_ERROR = (BusinessRuleError, "The file could not be saved.")


def build_file_key(bucket_id: uuid.UUID, file_id: uuid.UUID) -> str:
    """Object key in MinIO, built from ids so files with the same name never collide."""
    return f"buckets/{bucket_id}/{file_id}"


class FileService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.files = FileRepository(session)
        self.buckets = BucketRepository(session)
        self.folders = FolderRepository(session)
        self.users = UserRepository(session)

    def list_all(self) -> Sequence[File]:
        return self.files.get_all()

    def get(self, file_id: uuid.UUID) -> File:
        file = self.files.get_by_id(file_id)
        if file is None:
            raise NotFoundError(FILE_NOT_FOUND)
        return file

    def list_folders(self, bucket_id: uuid.UUID | None = None) -> Sequence[Folder]:
        """Folders of one bucket, or of every bucket when bucket_id is None."""
        if bucket_id is None:
            return self.folders.get_all()
        return self.folders.get_by_bucket(bucket_id)

    def create(
        self,
        bucket_id: uuid.UUID,
        uploader_id: uuid.UUID,
        filename: str,
        size_bytes: int,
        mime_type: str | None = None,
        folder_id: uuid.UUID | None = None,
        is_public: bool = False,
    ) -> File:
        """Save the file metadata and add its size to the bucket, in one transaction."""
        bucket = self.buckets.get_by_id(bucket_id)
        if bucket is None:
            raise NotFoundError(BUCKET_NOT_FOUND)
        uploader = self.users.get_by_id(uploader_id)
        if uploader is None:
            raise NotFoundError(UPLOADER_NOT_FOUND)
        self._check_upload(bucket, uploader, size_bytes)
        self._check_folder(folder_id, bucket_id)

        file_id = uuid.uuid4()
        try:
            file = self.files.add(
                file_id=file_id,
                file_key=build_file_key(bucket_id, file_id),
                filename=filename,
                size_bytes=size_bytes,
                bucket_id=bucket_id,
                uploader_id=uploader_id,
                mime_type=mime_type,
                folder_id=folder_id,
                is_public=is_public,
            )
            self.buckets.add_used_bytes(bucket_id, size_bytes)
            self.session.commit()
        except IntegrityError as error:
            self._raise_integrity_error(error)
        self.session.refresh(file)
        return file

    def update(
        self,
        file_id: uuid.UUID,
        filename: str,
        folder_id: uuid.UUID | None,
        is_public: bool,
    ) -> File:
        """Rename, move to another folder of the same bucket, or change visibility.
        Bucket, uploader and size are fixed after upload.
        """
        file = self.get(file_id)
        self._check_folder(folder_id, file.bucket_id)
        try:
            self.files.update(
                file, filename=filename, folder_id=folder_id, is_public=is_public
            )
            self.session.commit()
        except IntegrityError as error:
            self._raise_integrity_error(error)
        self.session.refresh(file)
        return file

    def _check_upload(self, bucket: Bucket, uploader: User, size_bytes: int) -> None:
        # Personal bucket: only the owner. Shared bucket: the owner and the members.
        allowed_ids = {bucket.owner_id} | {member.user_id for member in bucket.members}
        if uploader.id not in allowed_ids:
            raise PermissionDeniedError(
                f"{uploader.username} has no access to the bucket '{bucket.name}'."
            )

        if size_bytes < 0:
            raise BusinessRuleError(NEGATIVE_SIZE)
        max_file_size = uploader.tier_ref.max_file_size_bytes
        if size_bytes > max_file_size:
            raise BusinessRuleError(
                f"The file is larger than the {format_size(max_file_size)} limit "
                f"of the '{uploader.tier}' tier."
            )

        # Only personal buckets count toward the owner's storage quota.
        if not bucket.is_shared:
            owner = bucket.owner
            limit = owner.tier_ref.storage_limit_bytes
            used = self.buckets.used_bytes_by_owner(owner.id)
            if used + size_bytes > limit:
                free = max(limit - used, 0)
                raise BusinessRuleError(
                    f"Not enough storage: {owner.username} has {format_size(free)} free "
                    f"of {format_size(limit)} ('{owner.tier}' tier)."
                )

    def _check_folder(self, folder_id: uuid.UUID | None, bucket_id: uuid.UUID) -> None:
        if folder_id is None:  # bucket root
            return
        folder = self.folders.get_by_id(folder_id)
        if folder is None:
            raise NotFoundError(FOLDER_NOT_FOUND)
        if folder.bucket_id != bucket_id:
            raise BusinessRuleError(FOLDER_OUTSIDE_BUCKET)

    def _raise_integrity_error(self, error: IntegrityError) -> NoReturn:
        self.session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        error_class, message = CONSTRAINT_ERRORS.get(constraint, DEFAULT_ERROR)
        raise error_class(message) from error
