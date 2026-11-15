import uuid

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, templates
from app.core.security import hash_password
from app.repositories import TierRepository, UserRepository
from app.schemas import UserViewModel

router = APIRouter(prefix="/users", tags=["users"])

# Database constraint name -> message shown in the form.
CONSTRAINT_ERRORS = {
    "uq_users_email": "A user with this email already exists.",
    "uq_users_username": "A user with this username already exists.",
    "uq_users_referral_code": "Could not generate a unique referral code. Please try again.",
    "fk_users_tier_tiers": "The selected tier does not exist.",
}
DEFAULT_ERROR = "The user could not be saved."


def integrity_error_message(error: IntegrityError) -> str:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return CONSTRAINT_ERRORS.get(constraint, DEFAULT_ERROR)


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: UserViewModel,
    error: str | None = None,
):
    context = {"model": model, "tiers": TierRepository(session).get_all(), "error": error}
    return templates.TemplateResponse(request, view, context, status_code=400 if error else 200)


@router.get("")
def index(request: Request, session: DbSession):
    users = UserRepository(session).get_all()
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
        user = UserRepository(session).create(
            email=model.email,
            username=model.username,
            password_hash=hash_password(password),
            tier=model.tier,
            bio=model.bio,
            email_verified=model.email_verified,
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(request, session, "users/create.html", model, integrity_error_message(error))
    return RedirectResponse(f"/users/{user.id}", status_code=303)


@router.get("/{user_id}")
def details(request: Request, user_id: uuid.UUID, session: DbSession):
    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    model = UserViewModel.model_validate(user)
    return templates.TemplateResponse(request, "users/details.html", {"model": model})


@router.get("/{user_id}/edit")
def edit(request: Request, user_id: uuid.UUID, session: DbSession):
    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return render_form(request, session, "users/edit.html", UserViewModel.model_validate(user))


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
    model = UserViewModel(
        id=user_id,
        username=username.strip(),
        email=email.strip(),
        tier=tier,
        bio=bio.strip() or None,
        email_verified=email_verified,
    )
    try:
        user = UserRepository(session).update(
            user_id,
            email=model.email,
            username=model.username,
            tier=model.tier,
            bio=model.bio,
            email_verified=model.email_verified,
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(request, session, "users/edit.html", model, integrity_error_message(error))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(f"/users/{user_id}", status_code=303)
