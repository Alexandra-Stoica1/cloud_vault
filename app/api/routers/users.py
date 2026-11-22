import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_current_admin, templates
from app.schemas import UserViewModel
from app.services import ServiceError, UserService

# Server-rendered pages. Business rules live in UserService.
# Admins only: every page requires an admin session (see /login).
router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[Depends(get_current_admin)]
)


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: UserViewModel,
    error: str | None = None,
):
    context = {
        "model": model,
        "tiers": UserService(session).list_tiers(),
        "error": error,
    }
    return templates.TemplateResponse(
        request, view, context, status_code=400 if error else 200
    )


@router.get("")
def index(request: Request, session: DbSession):
    users = UserService(session).list_all()
    model = [UserViewModel.model_validate(user) for user in users]
    return templates.TemplateResponse(request, "users/index.html", {"model": model})


@router.get("/create")
def create(request: Request, session: DbSession):
    return render_form(request, session, "users/create.html", UserViewModel())


@router.post("/create")
def create_post(
    request: Request,
    session: DbSession,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    tier: str = Form(...),
    bio: str = Form(""),
    email_verified: bool = Form(False),
):
    model = UserViewModel(
        username=username.strip(),
        email=email.strip(),
        tier=tier,
        bio=bio.strip() or None,
        email_verified=email_verified,
    )
    try:
        user = UserService(session).create(
            email=model.email,
            username=model.username,
            password=password,
            tier=model.tier,
            bio=model.bio,
            email_verified=model.email_verified,
        )
    except ServiceError as error:
        return render_form(request, session, "users/create.html", model, error.message)
    return RedirectResponse(f"/users/{user.id}", status_code=303)


@router.get("/{user_id}")
def details(request: Request, user_id: uuid.UUID, session: DbSession):
    model = UserViewModel.model_validate(UserService(session).get(user_id))
    return templates.TemplateResponse(request, "users/details.html", {"model": model})


@router.get("/{user_id}/edit")
def edit(request: Request, user_id: uuid.UUID, session: DbSession):
    model = UserViewModel.model_validate(UserService(session).get(user_id))
    return render_form(request, session, "users/edit.html", model)


@router.post("/{user_id}/edit")
def edit_post(
    request: Request,
    user_id: uuid.UUID,
    session: DbSession,
    username: str = Form(...),
    email: str = Form(...),
    tier: str = Form(...),
    bio: str = Form(""),
    email_verified: bool = Form(False),
):
    service = UserService(session)
    service.get(user_id)  # 404 before showing the form again
    model = UserViewModel(
        id=user_id,
        username=username.strip(),
        email=email.strip(),
        tier=tier,
        bio=bio.strip() or None,
        email_verified=email_verified,
    )
    try:
        service.update(
            user_id,
            email=model.email,
            username=model.username,
            tier=model.tier,
            bio=model.bio,
            email_verified=model.email_verified,
        )
    except ServiceError as error:
        return render_form(request, session, "users/edit.html", model, error.message)
    return RedirectResponse(f"/users/{user_id}", status_code=303)
