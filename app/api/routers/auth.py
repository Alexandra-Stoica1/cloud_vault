from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import AuthService, TokenPair

router = APIRouter(prefix="/api/auth", tags=["auth"])


def to_token_response(tokens: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(body: RegisterRequest, session: DbSession):
    """Create an account. Returns 409 if the email or username is taken."""
    user = AuthService(session).register(body.email, body.username, body.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: DbSession):
    """Exchange email and password for an access token and a refresh token."""
    return to_token_response(AuthService(session).login(body.email, body.password))


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, session: DbSession):
    """Exchange a valid refresh token for a new token pair (the old one is revoked)."""
    return to_token_response(AuthService(session).refresh(body.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, session: DbSession) -> None:
    """Revoke the refresh token. Always returns 204."""
    AuthService(session).logout(body.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser):
    """Return the user identified by the access token (Authorization: Bearer ...)."""
    return UserResponse.model_validate(user)
