import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Folder


class FolderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> Sequence[Folder]:
        stmt = select(Folder).options(joinedload(Folder.bucket)).order_by(Folder.name)
        return self.session.scalars(stmt).all()

    def get_by_id(self, folder_id: uuid.UUID) -> Folder | None:
        return self.session.get(Folder, folder_id)

    def get_by_bucket(self, bucket_id: uuid.UUID) -> Sequence[Folder]:
        stmt = select(Folder).where(Folder.bucket_id == bucket_id).order_by(Folder.name)
        return self.session.scalars(stmt).all()
