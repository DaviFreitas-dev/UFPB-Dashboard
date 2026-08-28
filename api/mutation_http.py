import json
from typing import Annotated, TypeVar

from fastapi import Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError

from api.models import ApiModel
from api.mutations import NexoMutationError
from api.security import require_api_token


ApiModelT = TypeVar("ApiModelT", bound=ApiModel)


class MutationError(ApiModel):
    code: str
    message: str
    operation_id: str


class MutationErrorResponse(ApiModel):
    error: MutationError


def mutation_http_problem(status_code: int) -> tuple[str, str]:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "invalid_token", "Token inválido."
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "authentication_unavailable", "A autenticação da API está indisponível."
    return "request_failed", "A solicitação não pôde ser processada."


class MutationApiRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def guarded(request: Request):
            try:
                return await original(request)
            except HTTPException as error:
                code, message = mutation_http_problem(error.status_code)
                raise NexoMutationError(error.status_code, code, message) from error
            except RequestValidationError as error:
                raise NexoMutationError(
                    422,
                    "invalid_request",
                    "Revise os dados enviados.",
                ) from error

        return guarded


def require_mutation_api_token(
    x_nexo_token: Annotated[
        str | None,
        Header(alias="X-Nexo-Token", include_in_schema=False),
    ] = None,
) -> None:
    require_api_token(x_nexo_token)


async def validate_json_body(
    request: Request,
    model: type[ApiModelT],
) -> ApiModelT:
    try:
        return model.model_validate(await request.json())
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
        raise NexoMutationError(
            422,
            "invalid_request",
            "Revise os dados enviados.",
        ) from error
