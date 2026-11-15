import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bucket_invitation import BucketInvitation
    from app.models.bucket_member import BucketMember
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.user import User


class Bucket(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """Storage container.

    Personal buckets (is_shared = false) count toward the owner's tier quota:
    used quota = SUM(used_bytes) over the owner's personal buckets.
    ``used_bytes`` is a denormalized counter maintained by the file service.
    """

    __tablename__ = "buckets"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("used_bytes >= 0", name="used_bytes_non_negative"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    used_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )

    owner: Mapped["User"] = relationship(back_populates="buckets")
    members: Mapped[list["BucketMember"]] = relationship(
        back_populates="bucket", cascade="all, delete-orphan", passive_deletes=True
    )
    invitations: Mapped[list["BucketInvitation"]] = relationship(
        back_populates="bucket", cascade="all, delete-orphan", passive_deletes=True
    )
    folders: Mapped[list["Folder"]] = relationship(
        back_populates="bucket", cascade="all, delete-orphan", passive_deletes=True
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="bucket", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Bucket {self.name!r}>"
