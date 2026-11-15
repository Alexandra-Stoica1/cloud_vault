import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bucket import Bucket
    from app.models.file import File
    from app.models.user import User


class Folder(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Folder tree inside a bucket (parent_id NULL = bucket root).

    The composite FK (parent_id, bucket_id) -> folders(id, bucket_id) guarantees
    that a parent folder always belongs to the same bucket.
    """

    __tablename__ = "folders"
    __table_args__ = (
        # Target of the composite FKs from folders.parent_id and files.folder_id.
        UniqueConstraint("id", "bucket_id"),
        # No two sibling folders with the same name (NULLS NOT DISTINCT -> also at root level).
        UniqueConstraint(
            "bucket_id", "parent_id", "name", postgresql_nulls_not_distinct=True
        ),
        ForeignKeyConstraint(
            ["parent_id", "bucket_id"],
            ["folders.id", "folders.bucket_id"],
            name="fk_folders_parent_id_folders",
            ondelete="CASCADE",
        ),
    )

    bucket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable: deleting a user keeps the folders they created in someone else's bucket.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    bucket: Mapped["Bucket"] = relationship(back_populates="folders")
    parent: Mapped["Folder | None"] = relationship(
        back_populates="children",
        primaryjoin="Folder.parent_id == Folder.id",
        foreign_keys="Folder.parent_id",
        remote_side="Folder.id",
    )
    children: Mapped[list["Folder"]] = relationship(
        back_populates="parent",
        primaryjoin="Folder.parent_id == Folder.id",
        foreign_keys="Folder.parent_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    # passive_deletes="all": the ORM never touches files on folder delete; the database
    # FK (ON DELETE SET NULL (folder_id)) moves them to the bucket root.
    files: Mapped[list["File"]] = relationship(
        back_populates="folder",
        primaryjoin="File.folder_id == Folder.id",
        foreign_keys="File.folder_id",
        passive_deletes="all",
    )
    creator: Mapped["User | None"] = relationship()
