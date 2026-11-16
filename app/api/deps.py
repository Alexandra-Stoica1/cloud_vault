from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.db.session import get_db
from app.models import User
from app.repositories import UserRepository

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# Reads "Authorization: Bearer <token>"; also adds the Authorize button in /docs.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidAccessTokenError:
        raise unauthorized from None
    user = UserRepository(session).get_by_id(user_id)
    if user is None:  # the account was deleted after the token was issued
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

# Jinja2 templates shared by every router (app/views).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "views")
