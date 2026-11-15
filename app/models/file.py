import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.file_share import FileShare
    from app.models.folder import Folder
    from app.models.user import User


class File(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """File metadata. The content lives in object storage (MinIO) under ``file_key``.

    Build ``file_key`` from ids, not from the filename (e.g. ``buckets/{bucket_id}/{file_id}``),
    so two files with the same name never collide.
    """

    __tablename__ = "files"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="size_bytes_non_negative"),
        CheckConstraint("original_file_id IS NULL OR original_file_id <> id", name="original_not_self"),
        # The folder must belong to the same bucket as the file. When the folder is deleted
        # only folder_id is cleared, so the file moves to the bucket root (PostgreSQL 15+).
        ForeignKeyConstraint(
            ["folder_id", "bucket_id"], ["folders.id", "folders.bucket_id"],
            name="fk_files_folder_id_folders", ondelete="SET NULL (folder_id)",
        ),
        # Duplicate detection is done per uploader.
        Index(None, "uploader_id", "content_hash"),
    )

    bucket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(index=True)  # NULL = bucket root
    # Nullable: deleting a user keeps the files they uploaded to shared buckets.
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 hex
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # Set when is_duplicate is true: the file whose stored object this one reuses.
    original_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"), index=True
    )
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    bucket: Mapped["Bucket"] = relationship(back_populates="files")
    folder: Mapped["Folder | None"] = relationship(
        back_populates="files",
        primaryjoin="File.folder_id == Folder.id",
        foreign_keys="File.folder_id",
    )
    uploader: Mapped["User | None"] = relationship()
    original_file: Mapped["File | None"] = relationship(remote_side="File.id")
    shares: Mapped[list["FileShare"]] = relationship(
        back_populates="file", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<File {self.filename!r}>"
