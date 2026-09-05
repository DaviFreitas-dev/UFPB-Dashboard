import time
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from pydantic import AfterValidator, Field, StringConstraints, field_validator, model_validator

from api import mutations, sheets
from api.dashboard import _integer, _text
from api.models import ApiModel
from api.mutation_audit import log_mutation
from api.mutation_http import (
    MutationApiRoute,
    MutationErrorResponse,
    require_mutation_api_token,
    validate_json_body,
)
from api.mutations import NexoMutationError
from modules import reading


_MUTATION_ROUTE = "/v1/books"
_READING_WORKSHEET = "Leitura"
_TOKEN_HEADER = {
    "name": "X-Nexo-Token",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
}

router = APIRouter(
    prefix=_MUTATION_ROUTE,
    tags=["leitura"],
    route_class=MutationApiRoute,
)


def _validate_safe_reading_item_id(item_id):
    if not reading.is_safe_reading_item_id(item_id):
        raise ValueError("Identidade insegura.")
    return item_id


ReadingItemPathId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=reading.MAX_READING_ITEM_ID_LENGTH,
    ),
    AfterValidator(_validate_safe_reading_item_id),
    Path(),
]


class CreateBookRequest(ApiModel):
    id: UUID
    title: str = Field(min_length=1, max_length=160)
    author: str = Field(default="", max_length=120)
    total_pages: int = Field(strict=True, gt=0, le=1_000_000)
    daily_goal: int = Field(strict=True, gt=0, le=1_000_000)

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("title")
    @classmethod
    def require_title(cls, value):
        if not value:
            raise ValueError("O título é obrigatório.")
        return value


class ReadingMutationBook(ApiModel):
    id: str
    title: str
    author: str
    current_page: int
    total_pages: int
    daily_goal: int
    status: Literal["Lendo", "Concluído"]


class CreateBookResponse(ApiModel):
    operation_id: str
    created: bool
    book: ReadingMutationBook


class SetBookProgressRequest(ApiModel):
    current_page: int | None = Field(default=None, strict=True, ge=0, le=1_000_000)
    status: Literal["Lendo", "Concluído"] | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.current_page is None and self.status is None:
            raise ValueError("Informe uma alteração.")
        return self


class SetBookProgressResponse(ApiModel):
    operation_id: str
    changed: bool
    book: ReadingMutationBook


class DeleteBookResponse(ApiModel):
    operation_id: str
    id: str
    deleted: bool


async def parse_create_book_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> CreateBookRequest:
    return await validate_json_body(request, CreateBookRequest)


async def parse_set_book_progress_request(
    request: Request,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
) -> SetBookProgressRequest:
    return await validate_json_body(request, SetBookProgressRequest)


def _book(record):
    total = max(1, _integer(record.get("total_paginas"), 1))
    current = min(max(0, _integer(record.get("pagina_atual"))), total)
    status = _text(record.get("status"), "Lendo")
    if status not in {"Lendo", "Concluído"}:
        status = "Concluído" if current >= total else "Lendo"
    return ReadingMutationBook(
        id=_text(record.get("id")),
        title=_text(record.get("titulo"), "Livro sem título"),
        author=_text(record.get("autor")),
        current_page=current,
        total_pages=total,
        daily_goal=max(0, _integer(record.get("meta_diaria"))),
        status=status,
    )


def _log(request, *, item_id, route, outcome, status_code, started_at):
    log_mutation(
        request,
        domain="reading",
        resource_id=item_id,
        route=route,
        worksheets=(_READING_WORKSHEET,),
        outcome=outcome,
        status_code=status_code,
        started_at=started_at,
    )


@router.post(
    "",
    response_model=CreateBookResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        409: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={
        "parameters": [_TOKEN_HEADER],
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": CreateBookRequest.model_json_schema(by_alias=True)}},
        },
    },
)
def create_book(
    request: Request,
    payload: CreateBookRequest = Depends(parse_create_book_request),
):
    started_at = time.perf_counter()
    item_id = str(payload.id)
    try:
        with mutations.mutation_lock():
            record, created = reading.add(
                payload.title,
                payload.author,
                payload.total_pages,
                payload.daily_goal,
                item_id=item_id,
            )
        sheets.clear_dashboard_cache()
        response = CreateBookResponse(
            operation_id=request.state.operation_id,
            created=created,
            book=_book(record),
        )
    except reading.ReadingIdConflict as error:
        _log(request, item_id=item_id, route=_MUTATION_ROUTE, outcome="conflict", status_code=409, started_at=started_at)
        raise NexoMutationError(409, "idempotency_conflict", "Esta operação já foi usada com outro conteúdo.") from error
    except NexoMutationError as error:
        _log(request, item_id=item_id, route=_MUTATION_ROUTE, outcome="failure", status_code=error.status_code, started_at=started_at)
        raise
    except Exception as error:
        _log(request, item_id=item_id, route=_MUTATION_ROUTE, outcome="failure", status_code=503, started_at=started_at)
        raise NexoMutationError(503, "write_failed", "Não foi possível salvar o livro agora.") from error

    _log(request, item_id=item_id, route=_MUTATION_ROUTE, outcome="create" if response.created else "replay", status_code=200, started_at=started_at)
    return response


@router.patch(
    "/{item_id:path}",
    response_model=SetBookProgressResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        404: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={
        "parameters": [_TOKEN_HEADER],
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": SetBookProgressRequest.model_json_schema(by_alias=True)}},
        },
    },
)
def set_book_progress(
    request: Request,
    item_id: ReadingItemPathId,
    payload: SetBookProgressRequest = Depends(parse_set_book_progress_request),
):
    started_at = time.perf_counter()
    route = f"{_MUTATION_ROUTE}/{{item_id}}"
    try:
        with mutations.mutation_lock():
            record, changed = reading.set_progress(
                item_id,
                current_page=payload.current_page,
                status=payload.status,
            )
        if record is None:
            raise NexoMutationError(404, "record_not_found", "O livro não foi encontrado.")
        sheets.clear_dashboard_cache()
        response = SetBookProgressResponse(
            operation_id=request.state.operation_id,
            changed=changed,
            book=_book(record),
        )
    except ValueError as error:
        _log(request, item_id=item_id, route=route, outcome="failure", status_code=422, started_at=started_at)
        raise NexoMutationError(422, "invalid_request", "Revise os dados enviados.") from error
    except NexoMutationError as error:
        _log(request, item_id=item_id, route=route, outcome="failure", status_code=error.status_code, started_at=started_at)
        raise
    except Exception as error:
        _log(request, item_id=item_id, route=route, outcome="failure", status_code=503, started_at=started_at)
        raise NexoMutationError(503, "write_failed", "Não foi possível atualizar a leitura agora.") from error

    _log(request, item_id=item_id, route=route, outcome="update" if response.changed else "replay", status_code=200, started_at=started_at)
    return response


@router.delete(
    "/{item_id:path}",
    response_model=DeleteBookResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": MutationErrorResponse},
        422: {"model": MutationErrorResponse},
        503: {"model": MutationErrorResponse},
    },
    openapi_extra={"parameters": [_TOKEN_HEADER]},
)
def delete_book(
    request: Request,
    item_id: ReadingItemPathId,
    _token=Depends(require_mutation_api_token),
    _writes=Depends(mutations.require_api_writes),
):
    started_at = time.perf_counter()
    route = f"{_MUTATION_ROUTE}/{{item_id}}"
    try:
        with mutations.mutation_lock():
            deleted = reading.remove(item_id)
        sheets.clear_dashboard_cache()
        response = DeleteBookResponse(
            operation_id=request.state.operation_id,
            id=item_id,
            deleted=deleted,
        )
    except NexoMutationError as error:
        _log(request, item_id=item_id, route=route, outcome="failure", status_code=error.status_code, started_at=started_at)
        raise
    except Exception as error:
        _log(request, item_id=item_id, route=route, outcome="failure", status_code=503, started_at=started_at)
        raise NexoMutationError(503, "write_failed", "Não foi possível excluir o livro agora.") from error

    _log(request, item_id=item_id, route=route, outcome="delete" if response.deleted else "replay", status_code=200, started_at=started_at)
    return response
