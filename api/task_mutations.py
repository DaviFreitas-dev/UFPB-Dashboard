import json
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import Field, ValidationError, field_validator

from api.models import ApiModel
from api.mutations import NexoMutationError, mutation_lock, require_api_writes
from api.security import require_api_token
from api.sheets import clear_dashboard_cache
from modules import tasks


logger = logging.getLogger(__name__)


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


async def parse_create_task_request(
    request: Request,
    _token=Depends(require_api_token),
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
        raise NexoMutationError(
            409,
            "idempotency_conflict",
            "Esta operação já foi usada com outro conteúdo.",
        ) from error
    except NexoMutationError:
        raise
    except Exception as error:
        logger.error(
            "Falha ao criar tarefa. operation_id=%s error_type=%s",
            request.state.operation_id,
            type(error).__name__,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar a tarefa agora.",
        ) from error

    return response
