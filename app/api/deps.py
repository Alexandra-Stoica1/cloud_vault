from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import (
    ADMIN_SESSION_TOKEN,
    InvalidAccessTokenError,
    decode_access_token,
)
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

# Admin HTML pages: browsers cannot send a Bearer header, so the session token is kept
# in an HttpOnly, SameSite=Strict cookie set by the /login page.
ADMIN_SESSION_COOKIE = "cloudvault_admin_session"


class LoginRequiredError(Exception):
    """No valid admin session: the page redirects to /login, then back to ``next_path``."""

    def __init__(self, next_path: str) -> None:
        super().__init__(next_path)
        self.next_path = next_path


def get_current_admin(request: Request, session: DbSession) -> User:
    token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if token is None:
        raise LoginRequiredError(request.url.path)
    try:
        user_id = decode_access_token(token, token_type=ADMIN_SESSION_TOKEN)
    except InvalidAccessTokenError:  # expired, tampered or not a session token
        raise LoginRequiredError(request.url.path) from None
    user = UserRepository(session).get_by_id(user_id)
    if user is None:  # the account was deleted after the session started
        raise LoginRequiredError(request.url.path)
    if not user.is_admin:  # the admin flag was removed after the session started
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrators only."
        )
    request.state.admin = user  # shown in the navigation bar
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]

# Jinja2 templates shared by every router (app/views).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "views")
