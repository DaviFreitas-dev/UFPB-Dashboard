import json
import logging
import time
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import Field, ValidationError, field_validator

from api.models import ApiModel
from api.mutations import NexoMutationError, mutation_lock, require_api_writes
from api.security import require_api_token
from api.sheets import clear_dashboard_cache
from modules import tasks


logger = logging.getLogger(__name__)
_MUTATION_ROUTE = "/v1/tasks"
_TASK_WORKSHEET = "Tarefas"


def _log_task_mutation(
    request: Request,
    task_uuid: UUID,
    *,
    outcome: str,
    status_code: int,
    started_at: float,
) -> None:
    operation_id = request.state.operation_id
    event = {
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "event": "nexo.task.mutation",
        "operation_id": operation_id,
        "outcome": outcome,
        "request_id": operation_id,
        "route": _MUTATION_ROUTE,
        "status": status_code,
        "task_uuid": str(task_uuid),
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "worksheet": _TASK_WORKSHEET,
    }
    level = (
        logging.INFO
        if outcome in {"create", "replay"}
        else logging.WARNING
        if outcome == "conflict"
        else logging.ERROR
    )
    logger.log(level, json.dumps(event, ensure_ascii=False, sort_keys=True))


class TaskMutationRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def safe_validation_handler(request: Request):
            try:
                return await original_route_handler(request)
            except HTTPException as error:
                if error.status_code == 401:
                    code = "invalid_token"
                    message = "Token inválido."
                elif error.status_code == 503:
                    code = "authentication_unavailable"
                    message = "A autenticação da API está indisponível."
                else:
                    code = "request_failed"
                    message = "A solicitação não pôde ser processada."
                raise NexoMutationError(
                    error.status_code,
                    code,
                    message,
                ) from error
            except RequestValidationError as error:
                raise NexoMutationError(
                    422,
                    "invalid_request",
                    "Revise os dados enviados.",
                ) from error

        return safe_validation_handler


router = APIRouter(
    prefix="/v1/tasks",
    tags=["tarefas"],
    route_class=TaskMutationRoute,
)


class CreateTaskRequest(ApiModel):
    id: UUID
    date: date
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=40)

    @field_validator("title", "category")
    @classmethod
    def strip_required_text(cls, value):
        normalized = value.strip()
        if not normalized:
            raise ValueError("O campo não pode ficar vazio.")
        return normalized


class CreatedTask(ApiModel):
    id: str
    date: date
    title: str
    category: str
    completed: bool


class CreateTaskResponse(ApiModel):
    operation_id: str
    created: bool
    task: CreatedTask


class MutationError(ApiModel):
    code: str
    message: str
    operation_id: str


class MutationErrorResponse(ApiModel):
    error: MutationError


def require_task_api_token(
    x_nexo_token: Annotated[
        str | None,
        Header(alias="X-Nexo-Token", include_in_schema=False),
    ] = None,
):
    require_api_token(x_nexo_token)


async def parse_create_task_request(
    request: Request,
    _token=Depends(require_task_api_token),
    _writes=Depends(require_api_writes),
) -> CreateTaskRequest:
    try:
        body = await request.json()
        return CreateTaskRequest.model_validate(body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
        raise NexoMutationError(
            422,
            "invalid_request",
            "Revise os dados enviados.",
        ) from error


@router.post(
    "",
    response_model=CreateTaskResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse, "description": "Token inválido."},
        409: {
            "model": MutationErrorResponse,
            "description": "Conflito de idempotência.",
        },
        422: {
            "model": MutationErrorResponse,
            "description": "Dados inválidos.",
        },
        503: {
            "model": MutationErrorResponse,
            "description": "Escrita indisponível.",
        },
    },
    openapi_extra={
        "parameters": [
            {
                "name": "X-Nexo-Token",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": CreateTaskRequest.model_json_schema(by_alias=True),
                }
            },
        }
    },
)
def create_task(
    request: Request,
    payload: CreateTaskRequest = Depends(parse_create_task_request),
):
    started_at = time.perf_counter()
    try:
        with mutation_lock():
            record, created = tasks.add(
                payload.title,
                payload.category,
                payload.date,
                item_id=str(payload.id),
            )

        clear_dashboard_cache()
        response = CreateTaskResponse(
            operation_id=request.state.operation_id,
            created=created,
            task=CreatedTask(
                id=str(record["id"]),
                date=record["data"],
                title=str(record["tarefa"]),
                category=str(record["categoria"]),
                completed=str(record["status"]).lower()
                in {"concluída", "concluida"},
            ),
        )
    except tasks.TaskIdConflict as error:
        _log_task_mutation(
            request,
            payload.id,
            outcome="conflict",
            status_code=409,
            started_at=started_at,
        )
        raise NexoMutationError(
            409,
            "idempotency_conflict",
            "Esta operação já foi usada com outro conteúdo.",
        ) from error
    except NexoMutationError as error:
        _log_task_mutation(
            request,
            payload.id,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log_task_mutation(
            request,
            payload.id,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar a tarefa agora.",
        ) from error

    _log_task_mutation(
        request,
        payload.id,
        outcome="create" if response.created else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response
