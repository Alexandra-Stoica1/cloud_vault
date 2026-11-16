from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.exceptions import AuthenticationError, ConflictError, ServiceError

STATUS_BY_ERROR: dict[type[ServiceError], int] = {
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
}


async def service_error_handler(request: Request, error: ServiceError) -> JSONResponse:
    status_code = next(
        (code for cls, code in STATUS_BY_ERROR.items() if isinstance(error, cls)),
        status.HTTP_400_BAD_REQUEST,
    )
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        {"detail": error.message}, status_code=status_code, headers=headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, service_error_handler)
