import time
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from api.models import ApiModel
from api.mutation_audit import log_mutation
from api.mutation_http import (
    MutationApiRoute,
    MutationError,
    MutationErrorResponse,
    require_mutation_api_token,
    validate_json_body,
)
from api.mutations import NexoMutationError, mutation_lock, require_api_writes
from api.sheets import clear_dashboard_cache
from modules import tasks


_MUTATION_ROUTE = "/v1/tasks"
_TASK_WORKSHEET = "Tarefas"


router = APIRouter(
    prefix="/v1/tasks",
    tags=["tarefas"],
    route_class=MutationApiRoute,
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


async def parse_create_task_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(require_api_writes),
) -> CreateTaskRequest:
    return await validate_json_body(request, CreateTaskRequest)


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
        log_mutation(
            request,
            domain="task",
            resource_id=str(payload.id),
            route=_MUTATION_ROUTE,
            worksheets=(_TASK_WORKSHEET,),
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
        log_mutation(
            request,
            domain="task",
            resource_id=str(payload.id),
            route=_MUTATION_ROUTE,
            worksheets=(_TASK_WORKSHEET,),
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        log_mutation(
            request,
            domain="task",
            resource_id=str(payload.id),
            route=_MUTATION_ROUTE,
            worksheets=(_TASK_WORKSHEET,),
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar a tarefa agora.",
        ) from error

    log_mutation(
        request,
        domain="task",
        resource_id=str(payload.id),
        route=_MUTATION_ROUTE,
        worksheets=(_TASK_WORKSHEET,),
        outcome="create" if response.created else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response
