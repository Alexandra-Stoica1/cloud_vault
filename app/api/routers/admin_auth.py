from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import ADMIN_SESSION_COOKIE, AppSettings, DbSession, templates
from app.services import AuthService, ServiceError

# Login / logout for the admin HTML pages (the JSON API uses /api/auth instead).
router = APIRouter(tags=["admin session"], include_in_schema=False)

DEFAULT_NEXT = "/users"


def safe_next(next_path: str) -> str:
    """Only redirect to a path on this site, never to another domain ("//evil.com")."""
    if next_path.startswith("/") and not next_path.startswith(("//", "/\\")):
        return next_path
    return DEFAULT_NEXT


def render_login(
    request: Request, email: str, next_path: str, error: str | None = None
):
    context = {"email": email, "next": safe_next(next_path), "error": error}
    return templates.TemplateResponse(
        request, "login.html", context, status_code=400 if error else 200
    )


@router.get("/login")
def login(request: Request, next: str = DEFAULT_NEXT):
    return render_login(request, email="", next_path=next)


@router.post("/login")
def login_post(
    request: Request,
    session: DbSession,
    settings: AppSettings,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(DEFAULT_NEXT),
):
    email = email.strip()
    try:
        token, expires_in = AuthService(session).admin_login(email, password)
    except ServiceError as error:
        return render_login(request, email, next, error.message)

    response = RedirectResponse(safe_next(next), status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        token,
        max_age=expires_in,
        httponly=True,  # not readable from JavaScript
        samesite="strict",  # not sent by forms on other sites (CSRF)
        secure=not settings.debug,  # HTTPS only outside development
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ADMIN_SESSION_COOKIE, httponly=True, samesite="strict")
    return response
