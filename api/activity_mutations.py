import time
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from api import mutations, sheets
from api.dashboard import _completed, _text
from api.models import ApiModel
from api.mutation_audit import log_mutation
from api.mutation_http import (
    MutationApiRoute,
    MutationErrorResponse,
    require_mutation_api_token,
    validate_json_body,
)
from api.mutations import NexoMutationError
from modules import activity


_MUTATION_ROUTE = "/v1/activities"
_ACTIVITY_WORKSHEETS = ("Atividade", "XPEventos", "Usuario", "Historico")
_TOKEN_HEADER = {
    "name": "X-Nexo-Token",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
}


router = APIRouter(
    prefix=_MUTATION_ROUTE,
    tags=["atividade física"],
    route_class=MutationApiRoute,
)


class CreateActivityRequest(ApiModel):
    id: UUID
    date: date
    type: str = Field(min_length=1, max_length=40)

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        if not isinstance(value, str):
            return value
        return activity.normalize_activity_type(value)


class ConfirmedActivity(ApiModel):
    id: str | None
    date: date
    type: str
    completed: bool


class CreateActivityResponse(ApiModel):
    operation_id: str
    created: bool
    changed: bool
    activity: ConfirmedActivity


async def parse_create_activity_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> CreateActivityRequest:
    return await validate_json_body(request, CreateActivityRequest)


def _confirmed_activity(record):
    return ConfirmedActivity(
        id=_text(record.get("id")) or None,
        date=record["data"],
        type=_text(record.get("tipo")),
        completed=_completed(record.get("feito")),
    )


def _log(request, *, item_id, outcome, status_code, started_at):
    log_mutation(
        request,
        domain="activity",
        resource_id=item_id,
        route=_MUTATION_ROUTE,
        worksheets=_ACTIVITY_WORKSHEETS,
        outcome=outcome,
        status_code=status_code,
        started_at=started_at,
    )


@router.post(
    "",
    response_model=CreateActivityResponse,
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
                    "schema": CreateActivityRequest.model_json_schema(
                        by_alias=True
                    ),
                }
            },
        },
    },
)
def create_activity(
    request: Request,
    payload: CreateActivityRequest = Depends(parse_create_activity_request),
):
    started_at = time.perf_counter()
    item_id = str(payload.id)
    try:
        with mutations.mutation_lock():
            record, created, changed = activity.add(
                payload.type,
                payload.date,
                item_id=item_id,
            )
        sheets.clear_dashboard_cache()
        response = CreateActivityResponse(
            operation_id=request.state.operation_id,
            created=created,
            changed=changed,
            activity=_confirmed_activity(record),
        )
    except activity.ActivityIdConflict as error:
        _log(
            request,
            item_id=item_id,
            outcome="conflict",
            status_code=409,
            started_at=started_at,
        )
        raise NexoMutationError(
            409,
            "idempotency_conflict",
            "Esta atividade entra em conflito com um registro existente.",
        ) from error
    except NexoMutationError as error:
        _log(
            request,
            item_id=item_id,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            item_id=item_id,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível registrar a atividade agora.",
        ) from error

    _log(
        request,
        item_id=item_id,
        outcome="create" if response.created else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response
