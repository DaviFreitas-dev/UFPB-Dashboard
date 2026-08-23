import hmac
import os
from typing import Annotated

from fastapi import Header, HTTPException, status


def require_api_token(
    x_nexo_token: Annotated[str | None, Header(alias="X-Nexo-Token")] = None,
) -> None:
    expected = os.getenv("NEXO_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O token da API não foi configurado.",
        )
    if not x_nexo_token or not hmac.compare_digest(x_nexo_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        )
