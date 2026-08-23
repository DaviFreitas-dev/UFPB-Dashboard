import hmac
import logging
import os
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from api.dashboard import load_today_dashboard
from api.models import PlanningDashboard, RoutineDashboard, TodayDashboard
from api.personal import load_personal_workspace
from api.planning import load_planning_dashboard
from api.profile import load_profile_workspace
from api.routine import load_routine_dashboard
from api.studies import load_study_workspace
from api.workspace_models import PersonalWorkspace, ProfileWorkspace, StudyWorkspace


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


@app.get(
    "/v1/studies",
    response_model=StudyWorkspace,
    response_model_by_alias=True,
    tags=["estudos"],
)
def studies_workspace(_=Depends(require_api_token)):
    try:
        return load_study_workspace()
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar a área de estudos do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar a área de estudos.",
        ) from error


@app.get(
    "/v1/personal",
    response_model=PersonalWorkspace,
    response_model_by_alias=True,
    tags=["organização pessoal"],
)
def personal_workspace(
    target: Annotated[date | None, Query(alias="date")] = None,
    _=Depends(require_api_token),
):
    try:
        return load_personal_workspace(target)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar a organização pessoal do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar a organização pessoal.",
        ) from error


@app.get(
    "/v1/profile",
    response_model=ProfileWorkspace,
    response_model_by_alias=True,
    tags=["perfil"],
)
def profile_workspace(_=Depends(require_api_token)):
    try:
        return load_profile_workspace()
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Falha ao montar o perfil do NEXO.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar o perfil.",
        ) from error
