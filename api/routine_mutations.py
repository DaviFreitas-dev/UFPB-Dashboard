import time
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from api import mutations, sheets
from api.models import ApiModel
from api.mutation_audit import log_mutation
from api.mutation_http import (
    MutationApiRoute,
    MutationErrorResponse,
    require_mutation_api_token,
    validate_json_body,
)
from api.mutations import NexoMutationError
from modules import routine


_MUTATION_ROUTE = "/v1/routine-items"
_ROUTINE_WORKSHEET = "Rotina"
_TOKEN_HEADER = {
    "name": "X-Nexo-Token",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
}


router = APIRouter(
    prefix=_MUTATION_ROUTE,
    tags=["rotina"],
    route_class=MutationApiRoute,
)


class CreateRoutineItemRequest(ApiModel):
    id: UUID
    date: date
    time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title", mode="before")
    @classmethod
    def strip_required_title(cls, value):
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("A atividade é obrigatória.")
        return normalized


class RoutineMutationItem(ApiModel):
    id: str
    date: date
    time: str
    title: str
    completed: bool


class CreateRoutineItemResponse(ApiModel):
    operation_id: str
    created: bool
    item: RoutineMutationItem


class SetRoutineItemStateRequest(ApiModel):
    completed: bool = Field(strict=True)


class SetRoutineItemStateResponse(ApiModel):
    operation_id: str
    changed: bool
    item: RoutineMutationItem


class DeleteRoutineItemResponse(ApiModel):
    operation_id: str
    id: str
    deleted: bool


async def parse_create_routine_item_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> CreateRoutineItemRequest:
    return await validate_json_body(request, CreateRoutineItemRequest)


async def parse_set_routine_item_state_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> SetRoutineItemStateRequest:
    return await validate_json_body(request, SetRoutineItemStateRequest)


def _routine_item(record):
    return RoutineMutationItem(
        id=str(record["id"]),
        date=record["data"],
        time=str(record["hora"]),
        title=str(record.get("atividade") or "Compromisso sem título"),
        completed=str(record["status"]).casefold() in {"concluída", "concluida"},
    )


def _log(
    request,
    *,
    item_id,
    route,
    outcome,
    status_code,
    started_at,
):
    log_mutation(
        request,
        domain="routine",
        resource_id=item_id,
        route=route,
        worksheets=(_ROUTINE_WORKSHEET,),
        outcome=outcome,
        status_code=status_code,
        started_at=started_at,
    )


@router.post(
    "",
    response_model=CreateRoutineItemResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse, "description": "Token inválido."},
        409: {
            "model": MutationErrorResponse,
            "description": "Conflito de idempotência.",
        },
        422: {"model": MutationErrorResponse, "description": "Dados inválidos."},
        503: {
            "model": MutationErrorResponse,
            "description": "Escrita indisponível.",
        },
    },
    openapi_extra={
        "parameters": [_TOKEN_HEADER],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": CreateRoutineItemRequest.model_json_schema(
                        by_alias=True
                    ),
                }
            },
        },
    },
)
def create_routine_item(
    request: Request,
    payload: CreateRoutineItemRequest = Depends(
        parse_create_routine_item_request
    ),
):
    started_at = time.perf_counter()
    item_id = str(payload.id)
    try:
        with mutations.mutation_lock():
            record, created = routine.add(
                payload.title,
                payload.time,
                payload.date,
                item_id=item_id,
            )
        sheets.clear_dashboard_cache()
        response = CreateRoutineItemResponse(
            operation_id=request.state.operation_id,
            created=created,
            item=_routine_item(record),
        )
    except routine.RoutineIdConflict as error:
        _log(
            request,
            item_id=item_id,
            route=_MUTATION_ROUTE,
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
        _log(
            request,
            item_id=item_id,
            route=_MUTATION_ROUTE,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            item_id=item_id,
            route=_MUTATION_ROUTE,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar o compromisso agora.",
        ) from error

    _log(
        request,
        item_id=item_id,
        route=_MUTATION_ROUTE,
        outcome="create" if response.created else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response


@router.patch(
    "/{item_id}",
    response_model=SetRoutineItemStateResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse, "description": "Token inválido."},
        404: {
            "model": MutationErrorResponse,
            "description": "Compromisso não encontrado.",
        },
        422: {"model": MutationErrorResponse, "description": "Dados inválidos."},
        503: {
            "model": MutationErrorResponse,
            "description": "Escrita indisponível.",
        },
    },
    openapi_extra={
        "parameters": [_TOKEN_HEADER],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": SetRoutineItemStateRequest.model_json_schema(
                        by_alias=True
                    ),
                }
            },
        },
    },
)
def set_routine_item_state(
    request: Request,
    item_id: str,
    payload: SetRoutineItemStateRequest = Depends(
        parse_set_routine_item_state_request
    ),
):
    started_at = time.perf_counter()
    route = f"{_MUTATION_ROUTE}/{{item_id}}"
    try:
        with mutations.mutation_lock():
            record, changed = routine.set_completed(
                item_id,
                payload.completed,
            )
        if record is None:
            raise NexoMutationError(
                404,
                "record_not_found",
                "O compromisso não foi encontrado.",
            )
        sheets.clear_dashboard_cache()
        response = SetRoutineItemStateResponse(
            operation_id=request.state.operation_id,
            changed=changed,
            item=_routine_item(record),
        )
    except NexoMutationError as error:
        _log(
            request,
            item_id=item_id,
            route=route,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            item_id=item_id,
            route=route,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível atualizar o compromisso agora.",
        ) from error

    _log(
        request,
        item_id=item_id,
        route=route,
        outcome="update" if response.changed else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response


@router.delete(
    "/{item_id}",
    response_model=DeleteRoutineItemResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse, "description": "Token inválido."},
        422: {"model": MutationErrorResponse, "description": "Dados inválidos."},
        503: {
            "model": MutationErrorResponse,
            "description": "Escrita indisponível.",
        },
    },
    openapi_extra={"parameters": [_TOKEN_HEADER]},
)
def delete_routine_item(
    request: Request,
    item_id: str,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
):
    started_at = time.perf_counter()
    route = f"{_MUTATION_ROUTE}/{{item_id}}"
    try:
        with mutations.mutation_lock():
            deleted = routine.remove(item_id)
        sheets.clear_dashboard_cache()
        response = DeleteRoutineItemResponse(
            operation_id=request.state.operation_id,
            id=item_id,
            deleted=deleted,
        )
    except NexoMutationError as error:
        _log(
            request,
            item_id=item_id,
            route=route,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            item_id=item_id,
            route=route,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível excluir o compromisso agora.",
        ) from error

    _log(
        request,
        item_id=item_id,
        route=route,
        outcome="delete" if response.deleted else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response
