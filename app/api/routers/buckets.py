import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import DbSession, templates
from app.schemas import BucketViewModel
from app.services import BucketService, ServiceError, UserService

# Server-rendered pages. Business rules live in BucketService (shared with /api/buckets).
router = APIRouter(prefix="/buckets", tags=["buckets"])


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: BucketViewModel,
    error: str | None = None,
):
    context = {
        "model": model,
        "users": UserService(session).list_all(),
        "error": error,
    }
    return templates.TemplateResponse(
        request, view, context, status_code=400 if error else 200
    )


@router.get("")
def index(request: Request, session: DbSession):
    buckets = BucketService(session).list_all()
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
    try:
        bucket = BucketService(session).create(
            owner_id=owner_id,
            name=model.name,
            description=model.description,
            is_shared=model.is_shared,
        )
    except ServiceError as error:
        return render_form(
            request, session, "buckets/create.html", model, error.message
        )
    return RedirectResponse(f"/buckets/{bucket.id}", status_code=303)


@router.get("/{bucket_id}")
def details(request: Request, bucket_id: uuid.UUID, session: DbSession):
    model = BucketViewModel.from_entity(BucketService(session).get(bucket_id))
    return templates.TemplateResponse(request, "buckets/details.html", {"model": model})


@router.get("/{bucket_id}/edit")
def edit(request: Request, bucket_id: uuid.UUID, session: DbSession):
    model = BucketViewModel.from_entity(BucketService(session).get(bucket_id))
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
    service = BucketService(session)
    model = BucketViewModel.from_entity(service.get(bucket_id))
    model.name = name.strip()
    model.description = description.strip() or None
    try:
        service.update(bucket_id, name=model.name, description=model.description)
    except ServiceError as error:
        return render_form(request, session, "buckets/edit.html", model, error.message)
    return RedirectResponse(f"/buckets/{bucket_id}", status_code=303)
