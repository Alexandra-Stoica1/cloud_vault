from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routers import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, debug=settings.debug)
    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/users")

    return application


app = create_app()
