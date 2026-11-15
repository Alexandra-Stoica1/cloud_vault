from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# Jinja2 templates shared by every router (app/views).
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "views")
