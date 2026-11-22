import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_current_admin, templates
from app.schemas import FileViewModel
from app.services import BucketService, FileService, ServiceError, UserService

# Server-rendered pages. Business rules live in FileService.
# Admins only: every page requires an admin session (see /login).
router = APIRouter(
    prefix="/files", tags=["files"], dependencies=[Depends(get_current_admin)]
)


def parse_folder_id(value: str) -> uuid.UUID | None:
    """The folder select sends an empty string for "no folder"."""
    return uuid.UUID(value) if value else None


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: FileViewModel,
    error: str | None = None,
):
    # When editing, a file can only move between folders of its own bucket.
    folder_bucket_id = model.bucket_id if view == "files/edit.html" else None
    context = {
        "model": model,
        "buckets": BucketService(session).list_all(),
        "folders": FileService(session).list_folders(folder_bucket_id),
        "users": UserService(session).list_all(),
        "error": error,
    }
    return templates.TemplateResponse(
        request, view, context, status_code=400 if error else 200
    )


@router.get("")
def index(request: Request, session: DbSession):
    files = FileService(session).list_all()
    model = [FileViewModel.from_entity(file) for file in files]
    return templates.TemplateResponse(request, "files/index.html", {"model": model})


@router.get("/create")
def create(request: Request, session: DbSession):
    return render_form(request, session, "files/create.html", FileViewModel())


@router.post("/create")
def create_post(
    request: Request,
    session: DbSession,
    # Parameters without a default must come first.
    bucket_id: Annotated[uuid.UUID, Form()],
    uploader_id: Annotated[uuid.UUID, Form()],
    filename: str = Form(...),
    size_bytes: int = Form(...),
    mime_type: str = Form(""),
    folder_id: str = Form(""),
    is_public: bool = Form(False),
):
    model = FileViewModel(
        filename=filename.strip(),
        size_bytes=size_bytes,
        bucket_id=bucket_id,
        uploader_id=uploader_id,
        mime_type=mime_type.strip() or None,
        folder_id=parse_folder_id(folder_id),
        is_public=is_public,
    )
    try:
        file = FileService(session).create(
            bucket_id=bucket_id,
            uploader_id=uploader_id,
            filename=model.filename,
            size_bytes=model.size_bytes,
            mime_type=model.mime_type,
            folder_id=model.folder_id,
            is_public=model.is_public,
        )
    except ServiceError as error:
        return render_form(request, session, "files/create.html", model, error.message)
    return RedirectResponse(f"/files/{file.id}", status_code=303)


@router.get("/{file_id}")
def details(request: Request, file_id: uuid.UUID, session: DbSession):
    model = FileViewModel.from_entity(FileService(session).get(file_id))
    return templates.TemplateResponse(request, "files/details.html", {"model": model})


@router.get("/{file_id}/edit")
def edit(request: Request, file_id: uuid.UUID, session: DbSession):
    model = FileViewModel.from_entity(FileService(session).get(file_id))
    return render_form(request, session, "files/edit.html", model)


@router.post("/{file_id}/edit")
def edit_post(
    request: Request,
    file_id: uuid.UUID,
    session: DbSession,
    filename: str = Form(...),
    folder_id: str = Form(""),
    is_public: bool = Form(False),
):
    # Bucket, uploader and size are fixed after upload.
    service = FileService(session)
    model = FileViewModel.from_entity(service.get(file_id))
    model.filename = filename.strip()
    model.folder_id = parse_folder_id(folder_id)
    model.is_public = is_public
    try:
        service.update(
            file_id,
            filename=model.filename,
            folder_id=model.folder_id,
            is_public=model.is_public,
        )
    except ServiceError as error:
        return render_form(request, session, "files/edit.html", model, error.message)
    return RedirectResponse(f"/files/{file_id}", status_code=303)
