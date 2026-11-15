import uuid
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, templates
from app.repositories import BucketRepository, UserRepository
from app.schemas import BucketViewModel

router = APIRouter(prefix="/buckets", tags=["buckets"])

# Database constraint name -> message shown in the form.
CONSTRAINT_ERRORS = {
    "uq_buckets_owner_id_name": "This owner already has a bucket with this name.",
    "fk_buckets_owner_id_users": "The selected owner does not exist.",
}
DEFAULT_ERROR = "The bucket could not be saved."


def integrity_error_message(error: IntegrityError) -> str:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return CONSTRAINT_ERRORS.get(constraint, DEFAULT_ERROR)


def shared_bucket_limit_error(session: Session, owner_id: uuid.UUID) -> str | None:
    """Return an error if the owner's tier does not allow one more shared bucket."""
    owner = UserRepository(session).get_by_id(owner_id)
    if owner is None:
        return "The selected owner does not exist."
    limit = owner.tier_ref.max_shared_buckets  # NULL = unlimited
    if limit is None:
        return None
    if BucketRepository(session).count_shared_by_owner(owner_id) >= limit:
        if limit == 0:
            return f"The '{owner.tier}' tier does not allow shared buckets."
        return f"The '{owner.tier}' tier allows at most {limit} shared buckets."
    return None


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: BucketViewModel,
    error: str | None = None,
):
    context = {
        "model": model,
        "users": UserRepository(session).get_all(),
        "error": error,
    }
    return templates.TemplateResponse(
        request, view, context, status_code=400 if error else 200
    )


def get_bucket_or_404(session: Session, bucket_id: uuid.UUID):
    bucket = BucketRepository(session).get_by_id(bucket_id)
    if bucket is None:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return bucket


@router.get("")
def index(request: Request, session: DbSession):
    buckets = BucketRepository(session).get_all()
    model = [BucketViewModel.from_entity(bucket) for bucket in buckets]
    return templates.TemplateResponse(request, "buckets/index.html", {"model": model})


@router.get("/create")
def create(request: Request, session: DbSession):
    return render_form(request, session, "buckets/create.html", BucketViewModel())


@router.post("/create")
def create_post(
    request: Request,
    session: DbSession,
    # Parameters without a default must come first.
    owner_id: Annotated[uuid.UUID, Form()],
    name: str = Form(...),
    description: str = Form(""),
    is_shared: bool = Form(False),
):
    model = BucketViewModel(
        name=name.strip(),
        owner_id=owner_id,
        description=description.strip() or None,
        is_shared=is_shared,
    )
    if model.is_shared:
        error = shared_bucket_limit_error(session, owner_id)
        if error:
            return render_form(request, session, "buckets/create.html", model, error)
    try:
        bucket = BucketRepository(session).create(
            name=model.name,
            owner_id=owner_id,
            description=model.description,
            is_shared=model.is_shared,
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(
            request,
            session,
            "buckets/create.html",
            model,
            integrity_error_message(error),
        )
    return RedirectResponse(f"/buckets/{bucket.id}", status_code=303)


@router.get("/{bucket_id}")
def details(request: Request, bucket_id: uuid.UUID, session: DbSession):
    model = BucketViewModel.from_entity(get_bucket_or_404(session, bucket_id))
    return templates.TemplateResponse(request, "buckets/details.html", {"model": model})


@router.get("/{bucket_id}/edit")
def edit(request: Request, bucket_id: uuid.UUID, session: DbSession):
    model = BucketViewModel.from_entity(get_bucket_or_404(session, bucket_id))
    return render_form(request, session, "buckets/edit.html", model)


@router.post("/{bucket_id}/edit")
def edit_post(
    request: Request,
    bucket_id: uuid.UUID,
    session: DbSession,
    name: str = Form(...),
    description: str = Form(""),
):
    # Owner and shared flag are fixed after creation; only name and description can change.
    model = BucketViewModel.from_entity(get_bucket_or_404(session, bucket_id))
    model.name = name.strip()
    model.description = description.strip() or None
    try:
        BucketRepository(session).update(
            bucket_id, name=model.name, description=model.description
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(
            request, session, "buckets/edit.html", model, integrity_error_message(error)
        )
    return RedirectResponse(f"/buckets/{bucket_id}", status_code=303)
