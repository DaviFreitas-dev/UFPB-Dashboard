import hmac
import logging
import os
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from api.dashboard import load_today_dashboard
from api.models import PlanningDashboard, RoutineDashboard, TodayDashboard
from api.planning import load_planning_dashboard
from api.routine import load_routine_dashboard


logger = logging.getLogger(__name__)

app = FastAPI(
    title="NEXO API",
    description="Leitura segura dos dados usados pela nova interface do NEXO.",
    version="0.1.0",
)


def require_api_token(
    x_nexo_token: Annotated[
        str | None,
        Header(alias="X-Nexo-Token"),
    ] = None,
):
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


@app.get("/health", tags=["sistema"])
def health():
    return {"service": "nexo-api", "status": "ok"}


@app.get(
    "/v1/dashboard/today",
    response_model=TodayDashboard,
    response_model_by_alias=True,
    tags=["dashboard"],
)
def today_dashboard(_=Depends(require_api_token)):
    try:
        return load_today_dashboard()
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar o painel diário do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar os dados do painel.",
        ) from error


@app.get(
    "/v1/planning",
    response_model=PlanningDashboard,
    response_model_by_alias=True,
    tags=["planejamento"],
)
def planning_dashboard(_=Depends(require_api_token)):
    try:
        return load_planning_dashboard()
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar o planejamento do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar o planejamento.",
        ) from error


@app.get(
    "/v1/routine",
    response_model=RoutineDashboard,
    response_model_by_alias=True,
    tags=["rotina"],
)
def routine_dashboard(
    target: Annotated[date | None, Query(alias="date")] = None,
    _=Depends(require_api_token),
):
    try:
        return load_routine_dashboard(target)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar a rotina do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar a rotina.",
        ) from error
