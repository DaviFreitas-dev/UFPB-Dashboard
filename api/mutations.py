import os
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modules.gamification import xp_write_lock


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


class NexoMutationError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def api_writes_enabled() -> bool:
    return os.getenv("NEXO_API_WRITES_ENABLED", "").strip().lower() == "true"


def require_api_writes() -> None:
    if not api_writes_enabled():
        raise NexoMutationError(
            503,
            "writes_disabled",
            "As alterações estão temporariamente desativadas.",
        )


def mutation_lock():
    return xp_write_lock()


def install_mutation_support(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request.state.operation_id = (
            supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else uuid.uuid4().hex
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.operation_id
        return response

    @app.exception_handler(NexoMutationError)
    async def mutation_error(request: Request, error: NexoMutationError):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "operationId": request.state.operation_id,
                }
            },
        )
