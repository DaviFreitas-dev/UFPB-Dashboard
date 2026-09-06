import json
import logging
import time

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.testclient import TestClient

from api.models import ApiModel
from api.mutation_audit import log_mutation
from api.mutation_http import (
    MutationApiRoute,
    require_mutation_api_token,
    validate_json_body,
)
from api.mutations import install_mutation_support, require_api_writes


class MutationProbePayload(ApiModel):
    name: str


def build_mutation_probe_app():
    probe = FastAPI()
    install_mutation_support(probe)
    router = APIRouter(route_class=MutationApiRoute)

    async def parse_payload(
        request: Request,
        _token=Depends(require_mutation_api_token),
        _writes=Depends(require_api_writes),
    ) -> MutationProbePayload:
        return await validate_json_body(request, MutationProbePayload)

    @router.post("/test-mutation")
    async def test_mutation(
        payload: MutationProbePayload = Depends(parse_payload),
    ):
        return {"name": payload.name}

    probe.include_router(router)
    return probe


def test_guarded_route_checks_token_and_gate_before_json(monkeypatch):
    """Removing either guard allows malformed JSON to reach validation."""
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)

    response = TestClient(build_mutation_probe_app()).post(
        "/test-mutation",
        content=b"{broken",
        headers={
            "Content-Type": "application/json",
            "X-Nexo-Token": "server-test",
            "X-Request-ID": "guard-1",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_audit_event_contains_identifiers_but_not_private_content(caplog):
    """Logging a mutation must not gain a payload or token field."""
    request = Request({"type": "http", "method": "POST", "path": "/v1/tasks"})
    request.state.operation_id = "audit-1"
    caplog.set_level(logging.INFO, logger="api.mutation_audit")

    log_mutation(
        request,
        domain="task",
        resource_id="task-id",
        route="/v1/tasks",
        worksheets=("Tarefas",),
        outcome="update",
        status_code=200,
        started_at=time.perf_counter(),
    )

    event = json.loads(caplog.records[-1].message)
    assert event["resource_id"] == "task-id"
    assert event["worksheets"] == ["Tarefas"]
    assert "title" not in event
    assert "token" not in json.dumps(event).lower()
