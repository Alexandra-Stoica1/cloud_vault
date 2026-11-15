import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user(self, user_id: uuid.UUID, only_unread: bool = False) -> Sequence[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if only_unread:
            stmt = stmt.where(Notification.is_read.is_(False))
        return self.session.scalars(stmt.order_by(Notification.created_at.desc())).all()

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return self.session.get(Notification, notification_id)

    def create(self, user_id: uuid.UUID, title: str, message: str) -> Notification:
        notification = Notification(user_id=user_id, title=title, message=message)
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def mark_as_read(self, notification_id: uuid.UUID) -> bool:
        notification = self.get_by_id(notification_id)
        if notification is None:
            return False
        notification.is_read = True
        self.session.commit()
        return True

    def delete(self, notification_id: uuid.UUID) -> bool:
        notification = self.get_by_id(notification_id)
        if notification is None:
            return False
        self.session.delete(notification)
        self.session.commit()
        return True
