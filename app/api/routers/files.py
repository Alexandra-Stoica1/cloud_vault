import uuid
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, templates
from app.models import File
from app.repositories import (
    BucketRepository,
    FileRepository,
    FolderRepository,
    UserRepository,
)
from app.schemas import FileViewModel

router = APIRouter(prefix="/files", tags=["files"])

# Database constraint name -> message shown in the form.
CONSTRAINT_ERRORS = {
    "fk_files_bucket_id_buckets": "The selected bucket does not exist.",
    "fk_files_uploader_id_users": "The selected uploader does not exist.",
    "fk_files_folder_id_folders": "The selected folder does not belong to this bucket.",
    "ck_files_size_bytes_non_negative": "The size cannot be negative.",
}
DEFAULT_ERROR = "The file could not be saved."


def integrity_error_message(error: IntegrityError) -> str:
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return CONSTRAINT_ERRORS.get(constraint, DEFAULT_ERROR)


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} TB"


def parse_folder_id(value: str) -> uuid.UUID | None:
    """The folder select sends an empty string for "no folder"."""
    return uuid.UUID(value) if value else None


def folder_error(
    session: Session, folder_id: uuid.UUID | None, bucket_id: uuid.UUID
) -> str | None:
    if folder_id is None:
        return None
    folder = FolderRepository(session).get_by_id(folder_id)
    if folder is None:
        return "The selected folder does not exist."
    if folder.bucket_id != bucket_id:
        return "The selected folder does not belong to this bucket."
    return None


def upload_error(
    session: Session, bucket_id: uuid.UUID, uploader_id: uuid.UUID, size_bytes: int
) -> str | None:
    """Return an error if the upload breaks a business rule, otherwise None."""
    bucket = BucketRepository(session).get_by_id(bucket_id)
    if bucket is None:
        return "The selected bucket does not exist."
    uploader = UserRepository(session).get_by_id(uploader_id)
    if uploader is None:
        return "The selected uploader does not exist."

    # Personal bucket: only the owner. Shared bucket: the owner and the members.
    allowed_ids = {bucket.owner_id} | {member.user_id for member in bucket.members}
    if uploader.id not in allowed_ids:
        return f"{uploader.username} has no access to the bucket '{bucket.name}'."

    if size_bytes < 0:
        return "The size cannot be negative."
    max_file_size = uploader.tier_ref.max_file_size_bytes
    if size_bytes > max_file_size:
        return (
            f"The file is larger than the {format_size(max_file_size)} limit "
            f"of the '{uploader.tier}' tier."
        )

    # Only personal buckets count toward the owner's storage quota.
    if not bucket.is_shared:
        owner = bucket.owner
        limit = owner.tier_ref.storage_limit_bytes
        used = FileRepository(session).used_bytes_by_owner(owner.id)
        if used + size_bytes > limit:
            free = max(limit - used, 0)
            return (
                f"Not enough storage: {owner.username} has {format_size(free)} free "
                f"of {format_size(limit)} ('{owner.tier}' tier)."
            )
    return None


def render_form(
    request: Request,
    session: Session,
    view: str,
    model: FileViewModel,
    error: str | None = None,
):
    if model.bucket_id and view == "files/edit.html":
        # A file can only move between folders of its own bucket.
        folders = FolderRepository(session).get_by_bucket(model.bucket_id)
    else:
        folders = FolderRepository(session).get_all()
    context = {
        "model": model,
        "buckets": BucketRepository(session).get_all(),
        "folders": folders,
        "users": UserRepository(session).get_all(),
        "error": error,
    }
    return templates.TemplateResponse(
        request, view, context, status_code=400 if error else 200
    )


def get_file_or_404(session: Session, file_id: uuid.UUID) -> File:
    file = FileRepository(session).get_by_id(file_id)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@router.get("")
def index(request: Request, session: DbSession):
    files = FileRepository(session).get_all()
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
    error = upload_error(session, bucket_id, uploader_id, size_bytes) or folder_error(
        session, model.folder_id, bucket_id
    )
    if error:
        return render_form(request, session, "files/create.html", model, error)
    try:
        file = FileRepository(session).create(
            filename=model.filename,
            size_bytes=model.size_bytes,
            bucket_id=bucket_id,
            uploader_id=uploader_id,
            mime_type=model.mime_type,
            folder_id=model.folder_id,
            is_public=model.is_public,
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(
            request, session, "files/create.html", model, integrity_error_message(error)
        )
    return RedirectResponse(f"/files/{file.id}", status_code=303)


@router.get("/{file_id}")
def details(request: Request, file_id: uuid.UUID, session: DbSession):
    model = FileViewModel.from_entity(get_file_or_404(session, file_id))
    return templates.TemplateResponse(request, "files/details.html", {"model": model})


@router.get("/{file_id}/edit")
def edit(request: Request, file_id: uuid.UUID, session: DbSession):
    model = FileViewModel.from_entity(get_file_or_404(session, file_id))
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
    model = FileViewModel.from_entity(get_file_or_404(session, file_id))
    model.filename = filename.strip()
    model.folder_id = parse_folder_id(folder_id)
    model.is_public = is_public
    error = folder_error(session, model.folder_id, model.bucket_id)
    if error:
        return render_form(request, session, "files/edit.html", model, error)
    try:
        FileRepository(session).update(
            file_id,
            filename=model.filename,
            folder_id=model.folder_id,
            is_public=model.is_public,
        )
    except IntegrityError as error:
        session.rollback()
        return render_form(
            request, session, "files/edit.html", model, integrity_error_message(error)
        )
    return RedirectResponse(f"/files/{file_id}", status_code=303)
