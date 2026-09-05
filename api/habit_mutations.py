import time
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from pydantic import AfterValidator, Field, StringConstraints, field_validator

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
from api.personal import MAX_HABIT_CONFIG_ID_LENGTH, _safe_habit_config_id
from modules import habits
from modules.database import clear_records_cache


_HABITS_ROUTE = "/v1/habits"
_CHECKINS_ROUTE = "/v1/habit-checkins"
_HABIT_SHEETS = ("HabitosConfig", "Habitos")
_TOKEN_HEADER = {
    "name": "X-Nexo-Token",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
}

router = APIRouter(tags=["hábitos"], route_class=MutationApiRoute)


def _validate_config_id(value):
    if not _safe_habit_config_id(value):
        raise ValueError("Identidade insegura.")
    return value


HabitConfigPathId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_HABIT_CONFIG_ID_LENGTH,
    ),
    AfterValidator(_validate_config_id),
    Path(),
]


class CreateHabitRequest(ApiModel):
    id: UUID
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        if not isinstance(value, str):
            return value
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("O nome do hábito é obrigatório.")
        return normalized


class HabitMutationItem(ApiModel):
    config_id: str
    title: str
    active: bool


class CreateHabitResponse(ApiModel):
    operation_id: str
    created: bool
    reactivated: bool
    habit: HabitMutationItem


class SetHabitActiveRequest(ApiModel):
    active: bool = Field(strict=True)


class SetHabitActiveResponse(ApiModel):
    operation_id: str
    changed: bool
    habit: HabitMutationItem


class SetHabitCompletedRequest(ApiModel):
    completed: bool = Field(strict=True)


class HabitCheckin(ApiModel):
    config_id: str
    log_id: str | None
    date: date
    title: str
    completed: bool


class SetHabitCompletedResponse(ApiModel):
    operation_id: str
    changed: bool
    checkin: HabitCheckin


async def parse_create_habit_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> CreateHabitRequest:
    return await validate_json_body(request, CreateHabitRequest)


async def parse_set_habit_active_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> SetHabitActiveRequest:
    return await validate_json_body(request, SetHabitActiveRequest)


async def parse_set_habit_completed_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> SetHabitCompletedRequest:
    return await validate_json_body(request, SetHabitCompletedRequest)


def _habit(record):
    return HabitMutationItem(
        config_id=_text(record.get("id")),
        title=_text(record.get("nome"), "Hábito sem nome"),
        active=_completed(record.get("ativo")),
    )


def _checkin(record):
    return HabitCheckin(
        config_id=_text(record.get("config_id")),
        log_id=_text(record.get("id")) or None,
        date=record["data"],
        title=_text(record.get("habito"), "Hábito sem nome"),
        completed=_completed(record.get("feito")),
    )


def _clear_habit_caches():
    for name in _HABIT_SHEETS:
        clear_records_cache(name)
    sheets.clear_dashboard_cache()


def _log(request, *, resource_id, route, outcome, status_code, started_at):
    log_mutation(
        request,
        domain="habit",
        resource_id=resource_id,
        route=route,
        worksheets=_HABIT_SHEETS,
        outcome=outcome,
        status_code=status_code,
        started_at=started_at,
    )


@router.post(
    _HABITS_ROUTE,
    response_model=CreateHabitResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={"parameters": [_TOKEN_HEADER]},
)
def create_habit(
    request: Request,
    payload: CreateHabitRequest = Depends(parse_create_habit_request),
):
    started_at = time.perf_counter()
    config_id = str(payload.id)
    try:
        with mutations.mutation_lock():
            record, created, reactivated = habits.add(
                payload.name,
                item_id=config_id,
            )
        _clear_habit_caches()
        response = CreateHabitResponse(
            operation_id=request.state.operation_id,
            created=created,
            reactivated=reactivated,
            habit=_habit(record),
        )
    except NexoMutationError as error:
        _log(
            request,
            resource_id=config_id,
            route=_HABITS_ROUTE,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            resource_id=config_id,
            route=_HABITS_ROUTE,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar o hábito agora.",
        ) from error

    outcome = "create" if response.created else "reactivate" if response.reactivated else "replay"
    _log(
        request,
        resource_id=response.habit.config_id,
        route=_HABITS_ROUTE,
        outcome=outcome,
        status_code=200,
        started_at=started_at,
    )
    return response


@router.patch(
    f"{_HABITS_ROUTE}/{{config_id:path}}",
    response_model=SetHabitActiveResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        404: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={"parameters": [_TOKEN_HEADER]},
)
def set_habit_active(
    request: Request,
    config_id: HabitConfigPathId,
    payload: SetHabitActiveRequest = Depends(parse_set_habit_active_request),
):
    started_at = time.perf_counter()
    route = f"{_HABITS_ROUTE}/{{config_id}}"
    try:
        with mutations.mutation_lock():
            record, changed = habits.set_active(config_id, payload.active)
        if record is None:
            raise NexoMutationError(
                404,
                "record_not_found",
                "O hábito não foi encontrado.",
            )
        _clear_habit_caches()
        response = SetHabitActiveResponse(
            operation_id=request.state.operation_id,
            changed=changed,
            habit=_habit(record),
        )
    except NexoMutationError as error:
        _log(
            request,
            resource_id=config_id,
            route=route,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            resource_id=config_id,
            route=route,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível atualizar o hábito agora.",
        ) from error

    _log(
        request,
        resource_id=config_id,
        route=route,
        outcome="update" if response.changed else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response


@router.put(
    f"{_CHECKINS_ROUTE}/{{config_id:path}}/{{target_date}}",
    response_model=SetHabitCompletedResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        404: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={"parameters": [_TOKEN_HEADER]},
)
def set_habit_completed(
    request: Request,
    config_id: HabitConfigPathId,
    target_date: date,
    payload: SetHabitCompletedRequest = Depends(
        parse_set_habit_completed_request
    ),
):
    started_at = time.perf_counter()
    route = f"{_CHECKINS_ROUTE}/{{config_id}}/{{date}}"
    try:
        with mutations.mutation_lock():
            record, changed = habits.set_completed(
                config_id,
                target_date,
                payload.completed,
            )
        if record is None:
            raise NexoMutationError(
                404,
                "record_not_found",
                "O hábito não foi encontrado.",
            )
        _clear_habit_caches()
        response = SetHabitCompletedResponse(
            operation_id=request.state.operation_id,
            changed=changed,
            checkin=_checkin(record),
        )
    except NexoMutationError as error:
        _log(
            request,
            resource_id=config_id,
            route=route,
            outcome="failure",
            status_code=error.status_code,
            started_at=started_at,
        )
        raise
    except Exception as error:
        _log(
            request,
            resource_id=config_id,
            route=route,
            outcome="failure",
            status_code=503,
            started_at=started_at,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível atualizar o hábito agora.",
        ) from error

    _log(
        request,
        resource_id=config_id,
        route=route,
        outcome="update" if response.changed else "replay",
        status_code=200,
        started_at=started_at,
    )
    return response
