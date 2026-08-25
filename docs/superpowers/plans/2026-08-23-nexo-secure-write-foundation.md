# NEXO Secure Write Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir a fundação segura da nova interface do NEXO com login GitHub restrito, acesso Python ao Google Sheets independente do Streamlit e criação idempotente de tarefa como primeira mutação vertical, mantendo toda escrita desativada por padrão.

**Architecture:** O navegador autentica no Auth.js e chama apenas Server Actions do Next.js. O servidor Next.js revalida a identidade GitHub e usa `NEXO_API_TOKEN` para chamar o FastAPI; o FastAPI valida token e portão de escrita, serializa a mutação com o bloqueio Python existente e reutiliza `modules.tasks` para persistir no Google Sheets. A leitura em lote atual continua ativa, e os caches Python e Next.js só são invalidados depois da confirmação da escrita.

**Tech Stack:** Python 3, FastAPI 0.141.1, Pydantic, gspread, pytest, Next.js 16.3.2, React 19.2.8, TypeScript 6.0.3, Auth.js `next-auth` 5.0.0-beta.32, Zod 4.4.3, Vitest 4.1.11.

**Spec:** `docs/superpowers/specs/2026-08-23-nexo-write-migration-design.md`

## Canonical final-review errata (2026-08-25)

- The implemented private web gate is `NEXO_WEB_WRITES_ENABLED`. The earlier
  name `NEXO_MUTATIONS_UI_ENABLED` is obsolete and must not be used; this
  erratum overrides any historical snippet or operational note that retained
  that name.
- The accepted backfill contract is now a persisted, reviewable JSON plan:
  `--plan-out` generates exact worksheet/cell/row/UUID entries and
  `--apply-plan ... --confirm BACKFILL_IDS` consumes that same reviewed file.
- For any future real run, first enter maintenance and stop every Streamlit
  write path, then wait for in-flight requests and the maximum cache TTL.
  Generate, review, apply and verify the definitive plan while still
  quiescent. Keep both `NEXO_API_WRITES_ENABLED=false` and
  `NEXO_WEB_WRITES_ENABLED=false` through the end of that verification. This
  plan performs no operational action.

## Global Constraints

- O código atual da `main` prevalece sobre `AGENTS.md`; `AGENTS.md` prevalece sobre o histórico antigo.
- O nome visível permanece `NEXO`; não usar UFPB na interface.
- Manter `views/` e a navegação manual do Streamlit; nunca restaurar `pages/`.
- Nunca versionar `.streamlit/secrets.toml`, JSON de Service Account, tokens ou chaves reais.
- Manter a seção atual `st.secrets["gsheets"]`; não renomeá-la para o nome histórico.
- Preservar linhas e schemas legados; preencher apenas IDs vazios e nunca limpar uma aba para migrá-los.
- O cache de leitura continua com TTL de 15 segundos e só é invalidado depois de uma escrita confirmada.
- A API de produção deve recusar escritas quando `NEXO_API_WRITES_ENABLED` estiver ausente ou diferente de `true`.
- A interface deve esconder mutações quando `NEXO_WEB_WRITES_ENABLED` estiver ausente ou diferente de `true`.
- Autorização usa `NEXO_ALLOWED_GITHUB_ID`, o ID numérico imutável da conta `DaviFreitas-dev`; o login é apenas identificação visível.
- Nenhuma variável secreta poderá usar o prefixo `NEXT_PUBLIC_`.
- A primeira versão de escrita usa uma instância e um processo FastAPI.
- Toda Server Action autentica novamente perto do acesso aos dados; o `proxy.ts` é apenas a primeira barreira.
- Não executar escritas contra a planilha real durante este plano.
- Desenvolver cada comportamento com teste falhando primeiro e fazer commits pequenos usando apenas os arquivos daquela tarefa.

---

## File Structure

### Python

- `modules/sheets_credentials.py`: resolve credenciais do ambiente da API ou dos secrets atuais do Streamlit e expõe escopos somente leitura e leitura/escrita.
- `modules/database.py`: mantém o contrato atual de banco, mas troca decoradores Streamlit por caches Python com TTL e recursos reutilizáveis.
- `modules/id_backfill.py`: planeja e, somente com autorização explícita, preenche IDs vazios com UUIDs sem regravar abas.
- `modules/tasks.py`: aceita ID estável e torna a criação repetível com detecção de conflito.
- `api/security.py`: autentica o segredo entre Next.js e FastAPI.
- `api/mutations.py`: instala request ID, resposta de erro estável, portão de escrita e bloqueio compartilhado.
- `api/task_mutations.py`: expõe `POST /v1/tasks` e traduz o contrato HTTP para `modules.tasks`.
- `scripts/backfill_missing_ids.py`: oferece dry-run padrão e exige confirmação textual para aplicar o preenchimento.

### Next.js

- `web/src/auth.ts`: configura Auth.js, GitHub, JWT e allowlist por ID.
- `web/src/proxy.ts`: protege as rotas de aplicação sem substituir a autorização no servidor.
- `web/src/app/api/auth/[...nextauth]/route.ts`: publica os handlers oficiais do Auth.js.
- `web/src/lib/auth-policy.ts`: contém a política pura de identidade autorizada.
- `web/src/lib/auth-guard.ts`: revalida a sessão em leituras e mutações.
- `web/src/types/next-auth.d.ts`: adiciona `githubId` e `githubLogin` à sessão/JWT.
- `web/src/app/entrar/page.tsx` e `web/src/app/acesso-negado/page.tsx`: telas de entrada e recusa.
- `web/src/components/auth-shell.module.css`: estilo isolado dessas telas.
- `web/src/lib/nexo-api.ts`: cliente servidor-servidor tipado para leitura e mutação.
- `web/src/lib/write-policy.ts`: controla a exibição dos controles de edição.
- `web/src/app/tarefas/actions.ts`: valida o formulário e executa a criação no servidor.
- `web/src/components/task-create-form.tsx`: formulário cliente com ID estável, estado pendente e preservação de campos em falhas.

---

### Task 1: Shared Google credentials boundary

**Files:**
- Create: `modules/sheets_credentials.py`
- Create: `tests/test_sheets_credentials.py`
- Modify: `api/sheets.py:1-84`
- Test: `tests/test_api_sheets.py`

**Interfaces:**
- Produces: `READ_ONLY_SCOPES: tuple[str, ...]`
- Produces: `READ_WRITE_SCOPES: tuple[str, ...]`
- Produces: `load_service_account_info() -> dict[str, object]`
- Consumed by: `api.sheets._open_workbook()` and Task 2 `modules.database.connect_sheet()`

- [ ] **Step 1: Write failing credential tests**

```python
import json

import pytest

from modules import sheets_credentials


def test_credentials_prefer_server_environment(monkeypatch):
    expected = {"client_email": "service@example.test", "private_key": "test-only"}
    monkeypatch.setenv("GSHEETS_SERVICE_ACCOUNT_JSON", json.dumps(expected))
    monkeypatch.setattr(
        sheets_credentials,
        "_streamlit_service_account_info",
        lambda: pytest.fail("Streamlit fallback must not run"),
    )

    assert sheets_credentials.load_service_account_info() == expected


def test_credentials_reject_invalid_server_json(monkeypatch):
    monkeypatch.setenv("GSHEETS_SERVICE_ACCOUNT_JSON", "not-json")

    with pytest.raises(RuntimeError, match="JSON válido"):
        sheets_credentials.load_service_account_info()


def test_credentials_fall_back_to_current_streamlit_section(monkeypatch):
    monkeypatch.delenv("GSHEETS_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setattr(
        sheets_credentials,
        "_streamlit_service_account_info",
        lambda: {"client_email": "streamlit@example.test"},
    )

    assert sheets_credentials.load_service_account_info() == {
        "client_email": "streamlit@example.test"
    }
```

- [ ] **Step 2: Run the new tests and confirm the missing module failure**

Run: `python -m pytest tests/test_sheets_credentials.py -q`

Expected: FAIL during import because `modules.sheets_credentials` does not exist.

- [ ] **Step 3: Implement the shared credential loader**

```python
import json
import os


READ_ONLY_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)
READ_WRITE_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def _streamlit_service_account_info():
    import streamlit as st

    return dict(st.secrets["gsheets"])


def load_service_account_info():
    raw = os.getenv("GSHEETS_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "GSHEETS_SERVICE_ACCOUNT_JSON não contém um JSON válido."
            ) from error
        if not isinstance(info, dict):
            raise RuntimeError(
                "GSHEETS_SERVICE_ACCOUNT_JSON precisa conter um objeto JSON."
            )
        return info

    try:
        return _streamlit_service_account_info()
    except Exception as error:
        raise RuntimeError(
            "Configure GSHEETS_SERVICE_ACCOUNT_JSON ou a seção gsheets do Streamlit."
        ) from error
```

- [ ] **Step 4: Refactor the read-only API adapter to use the shared loader**

In `api/sheets.py`, remove its local JSON/Streamlit resolver and import:

```python
from modules.sheets_credentials import READ_ONLY_SCOPES, load_service_account_info
```

Build credentials with:

```python
credentials = Credentials.from_service_account_info(
    load_service_account_info(),
    scopes=READ_ONLY_SCOPES,
)
```

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/test_sheets_credentials.py tests/test_api_sheets.py -q`

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add modules/sheets_credentials.py api/sheets.py tests/test_sheets_credentials.py tests/test_api_sheets.py
git commit -m "refactor: compartilhar credenciais do Google Sheets"
```

### Task 2: Runtime-independent database cache

**Files:**
- Modify: `modules/database.py:1-154`
- Modify: `tests/test_database.py:1-83`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `load_service_account_info()` and `READ_WRITE_SCOPES` from Task 1
- Preserves: `connect_sheet()`, `get_worksheet(name)`, `records(name)`, `clear_records_cache(name=None)` and all write helper signatures
- Produces: `clear_resource_caches() -> None`, used only by tests and process lifecycle

- [ ] **Step 1: Replace direct Streamlit cache assertions with public-cache tests**

Add these tests and change existing calls from `database._records_cached.clear()` to `database.clear_records_cache()`:

```python
def test_records_cache_reuses_rows_until_cleared(monkeypatch):
    reads = []

    class ReadWorksheet:
        def get(self, **kwargs):
            reads.append(kwargs)
            return [
                SHEETS["Tarefas"],
                ["task-1", "2026-08-23", "Revisar", "Estudo", "Pendente"],
            ]

    monkeypatch.setattr(database, "get_worksheet", lambda _name: ReadWorksheet())
    database.clear_records_cache()

    first = database.records("Tarefas")
    first[0]["tarefa"] = "mudança local"
    second = database.records("Tarefas")

    assert second[0]["tarefa"] == "Revisar"
    assert len(reads) == 1
    database.clear_records_cache()


def test_database_module_has_no_top_level_streamlit_dependency():
    source = Path(database.__file__).read_text(encoding="utf-8")

    assert "import streamlit as st" not in source
    assert "@st.cache_" not in source
```

Import `Path` from `pathlib` in the test file.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m pytest tests/test_database.py -q`

Expected: FAIL because the current module still imports Streamlit and the current cache does not expose the required runtime-independent implementation.

- [ ] **Step 3: Replace Streamlit resource decorators with Python resource caches**

At the top of `modules/database.py`, use:

```python
import copy
import json
import re
import threading
import time
import uuid
from datetime import date
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials
from gspread.http_client import BackOffHTTPClient
from gspread.utils import numericise_all, to_records

from modules.config import CICLO_PADRAO, SHEETS, XP_POR_HORA
from modules.sheets_credentials import READ_WRITE_SCOPES, load_service_account_info


_CACHE_SECONDS = 15
_RECORDS_CACHE_LOCK = threading.RLock()
_RECORDS_CACHE = {}


@lru_cache(maxsize=1)
def connect_sheet():
    creds = Credentials.from_service_account_info(
        load_service_account_info(),
        scopes=READ_WRITE_SCOPES,
    )
    client = gspread.authorize(creds, http_client=BackOffHTTPClient)
    return client.open("Banco_UFPB")


@lru_cache(maxsize=1)
def _worksheets_by_name():
    return {ws.title: ws for ws in connect_sheet().worksheets()}
```

Keep `get_worksheet()` as a regular function protected by `_RECORDS_CACHE_LOCK` so creation of a missing worksheet remains serialized.

- [ ] **Step 4: Implement a 15-second copy-safe records cache**

Replace the decorated `_records_cached()` and current clear helper with:

```python
def _read_records(name):
    ws = get_worksheet(name)
    entire_sheet = ws.get(pad_values=True)
    if entire_sheet == [[]]:
        entire_sheet = []
    current = entire_sheet[0] if entire_sheet else []
    _ensure_header(name, ws, current=current)
    if not entire_sheet:
        return []
    values = [
        numericise_all(row, False, "", False, [])
        for row in entire_sheet[1:]
    ]
    return to_records(current, values)


def _records_cached(name):
    now = time.monotonic()
    with _RECORDS_CACHE_LOCK:
        cached = _RECORDS_CACHE.get(name)
        if cached and now < cached[0]:
            return copy.deepcopy(cached[1])
        rows = _read_records(name)
        _RECORDS_CACHE[name] = (now + _CACHE_SECONDS, copy.deepcopy(rows))
        return copy.deepcopy(rows)


def clear_records_cache(name=None):
    with _RECORDS_CACHE_LOCK:
        if name is None:
            _RECORDS_CACHE.clear()
        else:
            _RECORDS_CACHE.pop(name, None)


def clear_resource_caches():
    clear_records_cache()
    _worksheets_by_name.cache_clear()
    connect_sheet.cache_clear()
```

Remove the presentation-side `st.error()` call from `records()` and let FastAPI or Streamlit handle the raised `gspread.exceptions.APIError` at its own boundary:

```python
def records(name):
    return [dict(row) for row in _records_cached(name)]
```

- [ ] **Step 5: Make initialization cacheable without Streamlit**

Decorate `initialize_database()` with `@lru_cache(maxsize=1)` and extend `clear_resource_caches()` to call `initialize_database.cache_clear()` after the function has been defined. Keep legacy migration and default creation in the same order.

- [ ] **Step 6: Run database and import checks**

Run: `python -m pytest tests/test_database.py tests/test_gamification.py tests/test_study_sessions.py -q`

Run: `python -m compileall -q modules api views`

Expected: both commands succeed without Streamlit context warnings from importing `modules.database`.

- [ ] **Step 7: Commit Task 2**

```bash
git add modules/database.py tests/test_database.py
git commit -m "refactor: desacoplar banco do contexto Streamlit"
```

### Task 3: API mutation safety boundary

**Files:**
- Create: `api/security.py`
- Create: `api/mutations.py`
- Create: `tests/test_api_mutations.py`
- Modify: `api/main.py:1-45`
- Modify: `tests/test_api_main.py:1-45`

**Interfaces:**
- Produces: `require_api_token(x_nexo_token: str | None) -> None`
- Produces: `require_api_writes() -> None`
- Produces: `mutation_lock()` returning the existing reentrant XP lock
- Produces: `NexoMutationError(status_code, code, message)`
- Produces: `install_mutation_support(app: FastAPI) -> None`
- Consumed by: Task 6 API task router

- [ ] **Step 1: Write failing security and error-contract tests**

```python
import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.mutations import install_mutation_support, require_api_writes


def build_probe_app():
    probe = FastAPI()
    install_mutation_support(probe)

    @probe.post("/probe")
    def write_probe(_=Depends(require_api_writes)):
        return {"ok": True}

    return probe


def test_write_gate_is_closed_when_environment_is_missing(monkeypatch):
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    response = TestClient(build_probe_app()).post("/probe")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"
    assert response.json()["error"]["operationId"]
    assert response.headers["X-Request-ID"]


def test_write_gate_accepts_only_explicit_true(monkeypatch):
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")

    response = TestClient(build_probe_app()).post(
        "/probe",
        headers={"X-Request-ID": "request-test-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-test-1"
```

- [ ] **Step 2: Run the tests and confirm the missing module failure**

Run: `python -m pytest tests/test_api_mutations.py -q`

Expected: FAIL because `api.mutations` does not exist.

- [ ] **Step 3: Extract the existing server-token dependency**

Create `api/security.py` with the current constant-time comparison from `api/main.py`:

```python
import hmac
import os
from typing import Annotated

from fastapi import Header, HTTPException, status


def require_api_token(
    x_nexo_token: Annotated[str | None, Header(alias="X-Nexo-Token")] = None,
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
```

Import this dependency from `api.main` and remove the duplicate function there.

- [ ] **Step 4: Implement request IDs, stable mutation errors and the closed gate**

Create `api/mutations.py` with these public behaviors:

```python
import os
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modules.gamification import xp_write_lock


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")


class NexoMutationError(RuntimeError):
    def __init__(self, status_code, code, message):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def api_writes_enabled():
    return os.getenv("NEXO_API_WRITES_ENABLED", "").strip().lower() == "true"


def require_api_writes():
    if not api_writes_enabled():
        raise NexoMutationError(
            503,
            "writes_disabled",
            "As alterações estão temporariamente desativadas.",
        )


def mutation_lock():
    return xp_write_lock()


def install_mutation_support(app: FastAPI):
    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request.state.operation_id = (
            supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else uuid.uuid4().hex
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.operation_id
        return response

    @app.exception_handler(NexoMutationError)
    async def mutation_error(request: Request, error: NexoMutationError):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "operationId": request.state.operation_id,
                }
            },
        )
```

Call `install_mutation_support(app)` once immediately after creating the FastAPI application.

- [ ] **Step 5: Run API safety tests**

Run: `python -m pytest tests/test_api_mutations.py tests/test_api_main.py -q`

Expected: PASS; existing read routes still use the same token behavior.

- [ ] **Step 6: Commit Task 3**

```bash
git add api/security.py api/mutations.py api/main.py tests/test_api_mutations.py tests/test_api_main.py
git commit -m "feat: adicionar fronteira segura de mutacoes"
```

### Task 4: Idempotent legacy ID backfill utility

**Files:**
- Create: `modules/id_backfill.py`
- Create: `scripts/backfill_missing_ids.py`
- Create: `tests/test_id_backfill.py`

**Interfaces:**
- Produces: `ID_SHEETS: tuple[str, ...]`
- Produces: `collect_missing_id_updates(name, rows, id_factory) -> list[dict[str, object]]`
- Produces: `backfill_missing_ids(apply=False) -> dict[str, int]`
- Constraint: this task creates and tests the utility but never runs it against the live workbook

- [ ] **Step 1: Write failing pure backfill tests**

```python
from modules.id_backfill import collect_missing_id_updates


def test_backfill_only_targets_empty_id_cells():
    ids = iter(["generated-1", "generated-2"])
    rows = [
        ["id", "data", "tarefa", "categoria", "status"],
        ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
        ["kept-id", "2026-08-23", "Treinar", "Saúde", "Concluída"],
        ["", "2026-08-24", "Ler", "Pessoal", "Pendente"],
    ]

    updates = collect_missing_id_updates(
        "Tarefas",
        rows,
        id_factory=lambda: next(ids),
    )

    assert updates == [
        {"sheet": "Tarefas", "range": "A2", "values": [["generated-1"]]},
        {"sheet": "Tarefas", "range": "A4", "values": [["generated-2"]]},
    ]


def test_backfill_is_empty_after_ids_exist():
    rows = [
        ["id", "data", "tarefa", "categoria", "status"],
        ["task-1", "2026-08-22", "Revisar", "Estudo", "Pendente"],
    ]

    assert collect_missing_id_updates("Tarefas", rows, id_factory=lambda: "unused") == []
```

- [ ] **Step 2: Run the test and confirm the missing module failure**

Run: `python -m pytest tests/test_id_backfill.py -q`

Expected: FAIL because `modules.id_backfill` does not exist.

- [ ] **Step 3: Implement the pure planner and dry-run-safe executor**

```python
import uuid

from modules.config import SHEETS
from modules.database import get_worksheet, write_values_batch


ID_SHEETS = tuple(name for name, columns in SHEETS.items() if "id" in columns)


def collect_missing_id_updates(name, rows, id_factory=None):
    if not rows:
        return []
    header = [str(value).strip() for value in rows[0]]
    if header != SHEETS[name]:
        raise RuntimeError(f"A aba '{name}' não possui o cabeçalho esperado.")
    id_column = header.index("id")
    make_id = id_factory or (lambda: str(uuid.uuid4()))
    updates = []
    for row_number, row in enumerate(rows[1:], start=2):
        has_content = any(str(value).strip() for value in row)
        current_id = row[id_column] if id_column < len(row) else ""
        if has_content and not str(current_id).strip():
            updates.append(
                {
                    "sheet": name,
                    "range": f"A{row_number}",
                    "values": [[make_id()]],
                }
            )
    return updates


def backfill_missing_ids(apply=False):
    updates = []
    counts = {}
    for name in ID_SHEETS:
        rows = get_worksheet(name).get(pad_values=True)
        sheet_updates = collect_missing_id_updates(name, rows)
        updates.extend(sheet_updates)
        counts[name] = len(sheet_updates)
    if apply and updates:
        write_values_batch(updates)
    return counts
```

- [ ] **Step 4: Add a CLI that defaults to dry-run and requires exact confirmation**

`scripts/backfill_missing_ids.py` must use this decision boundary:

```python
import argparse
import hmac

from modules.id_backfill import backfill_missing_ids


def should_apply(apply, confirmation):
    return bool(apply) and hmac.compare_digest(confirmation, "BACKFILL_IDS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.apply and not should_apply(args.apply, args.confirm):
        parser.error("Use --apply --confirm BACKFILL_IDS para gravar.")
    counts = backfill_missing_ids(apply=should_apply(args.apply, args.confirm))
    for name, count in counts.items():
        print(f"{name}: {count} ID(s) ausente(s)")


if __name__ == "__main__":
    main()
```

Add these pure assertions to `tests/test_id_backfill.py`; do not invoke `main()` or Google Sheets:

```python
from scripts.backfill_missing_ids import should_apply


def test_backfill_cli_requires_exact_confirmation():
    assert should_apply(True, "BACKFILL_IDS") is True
    assert should_apply(True, "backfill_ids") is False
    assert should_apply(False, "BACKFILL_IDS") is False
```

- [ ] **Step 5: Run utility tests without live credentials**

Run: `python -m pytest tests/test_id_backfill.py -q`

Expected: PASS and no network access.

- [ ] **Step 6: Commit Task 4**

```bash
git add modules/id_backfill.py scripts/backfill_missing_ids.py tests/test_id_backfill.py
git commit -m "feat: preparar preenchimento seguro de ids legados"
```

### Task 5: Idempotent task creation in the Python domain

**Files:**
- Modify: `modules/tasks.py:1-31`
- Create: `tests/test_tasks.py`

**Interfaces:**
- Produces: `TaskIdConflict(ValueError)`
- Changes: `add(task, category, target_date=None, item_id=None) -> tuple[dict[str, object], bool]`
- Return meaning: `(record, True)` for a new row and `(existing_record, False)` for an identical retry
- Preserves: existing Streamlit calls that ignore the return value and omit `item_id`

- [ ] **Step 1: Write failing idempotency tests**

```python
from datetime import date

import pytest

from modules import tasks


def test_add_uses_stable_id_and_returns_created_record(monkeypatch):
    appended = []
    monkeypatch.setattr(tasks, "records", lambda _name: [])
    monkeypatch.setattr(tasks, "append_record", lambda name, values: appended.append((name, values)))

    record, created = tasks.add(
        "Revisar matemática",
        "Estudo",
        date(2026, 8, 23),
        item_id="task-stable-id",
    )

    assert created is True
    assert record["id"] == "task-stable-id"
    assert appended == [
        (
            "Tarefas",
            ["task-stable-id", "2026-08-23", "Revisar matemática", "Estudo", "Pendente"],
        )
    ]


def test_add_returns_existing_record_for_identical_retry(monkeypatch):
    existing = {
        "id": "task-stable-id",
        "data": "2026-08-23",
        "tarefa": "Revisar matemática",
        "categoria": "Estudo",
        "status": "Concluída",
    }
    monkeypatch.setattr(tasks, "records", lambda _name: [existing])
    monkeypatch.setattr(
        tasks,
        "append_record",
        lambda _name, _values: pytest.fail("retry must not append"),
    )

    assert tasks.add(
        "Revisar matemática",
        "Estudo",
        date(2026, 8, 23),
        item_id="task-stable-id",
    ) == (existing, False)


def test_add_rejects_same_id_with_different_content(monkeypatch):
    monkeypatch.setattr(
        tasks,
        "records",
        lambda _name: [{
            "id": "task-stable-id",
            "data": "2026-08-23",
            "tarefa": "Conteúdo anterior",
            "categoria": "Estudo",
            "status": "Pendente",
        }],
    )

    with pytest.raises(tasks.TaskIdConflict):
        tasks.add(
            "Novo conteúdo",
            "Estudo",
            date(2026, 8, 23),
            item_id="task-stable-id",
        )
```

- [ ] **Step 2: Run the tests and confirm signature/behavior failures**

Run: `python -m pytest tests/test_tasks.py -q`

Expected: FAIL because `add()` does not accept `item_id` and does not return creation metadata.

- [ ] **Step 3: Implement stable creation without changing toggle XP rules**

```python
class TaskIdConflict(ValueError):
    pass


def add(task, category, target_date=None, item_id=None):
    target = target_date or date.today()
    task_text = str(task).strip()
    category_text = str(category).strip()
    if not task_text or not category_text:
        raise ValueError("Tarefa e categoria são obrigatórias.")

    record_id = str(item_id or new_id())
    expected = {
        "id": record_id,
        "data": str(target),
        "tarefa": task_text,
        "categoria": category_text,
        "status": "Pendente",
    }
    existing = next(
        (row for row in records("Tarefas") if str(row.get("id")) == record_id),
        None,
    )
    if existing is not None:
        immutable_fields = ("id", "data", "tarefa", "categoria")
        comparable = {
            key: str(existing.get(key, ""))
            for key in immutable_fields
        }
        requested = {
            key: str(expected[key])
            for key in immutable_fields
        }
        if comparable == requested:
            return existing, False
        raise TaskIdConflict("O ID da tarefa já existe com outro conteúdo.")

    append_record(
        "Tarefas",
        [expected[column] for column in ("id", "data", "tarefa", "categoria", "status")],
    )
    return expected, True
```

Keep `toggle()` and its `event_key=f"task:{item_id}"` unchanged.

- [ ] **Step 4: Run domain and XP tests**

Run: `python -m pytest tests/test_tasks.py tests/test_gamification.py -q`

Expected: PASS; task completion still deduplicates XP through the existing event key.

- [ ] **Step 5: Commit Task 5**

```bash
git add modules/tasks.py tests/test_tasks.py
git commit -m "feat: tornar criacao de tarefa idempotente"
```

### Task 6: First protected FastAPI mutation

**Files:**
- Create: `api/task_mutations.py`
- Create: `tests/test_api_task_mutations.py`
- Modify: `api/main.py:1-22`

**Interfaces:**
- Produces: `POST /v1/tasks`
- Request: `{ "id": UUID, "date": YYYY-MM-DD, "title": string, "category": string }`
- Response: `{ "operationId", "created", "task": { "id", "date", "title", "category", "completed" } }`
- Requires: `X-Nexo-Token` and `NEXO_API_WRITES_ENABLED=true`
- Consumes: `modules.tasks.add()`, `mutation_lock()` and `api.sheets.clear_dashboard_cache()`

- [ ] **Step 1: Write failing endpoint tests with all writes mocked**

```python
from fastapi.testclient import TestClient

import api.task_mutations as task_mutations
from api.main import app


client = TestClient(app)
HEADERS = {"X-Nexo-Token": "server-test", "X-Request-ID": "task-request-1"}
PAYLOAD = {
    "id": "0f3ac9b0-5779-40ce-834d-40a8657684af",
    "date": "2026-08-23",
    "title": "Revisar matemática",
    "category": "Estudo",
}


def enable_mutations(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.setenv("NEXO_API_WRITES_ENABLED", "true")


def test_task_creation_is_blocked_by_default(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_task_creation_returns_confirmed_record_and_clears_read_cache(monkeypatch):
    enable_mutations(monkeypatch)
    cleared = []
    monkeypatch.setattr(
        task_mutations.tasks,
        "add",
        lambda title, category, target, item_id: ({
            "id": item_id,
            "data": str(target),
            "tarefa": title,
            "categoria": category,
            "status": "Pendente",
        }, True),
    )
    monkeypatch.setattr(task_mutations, "clear_dashboard_cache", lambda: cleared.append(True))

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["created"] is True
    assert response.json()["task"]["id"] == PAYLOAD["id"]
    assert response.json()["operationId"] == "task-request-1"
    assert cleared == [True]


def test_task_creation_maps_id_conflict_without_leaking_content(monkeypatch):
    enable_mutations(monkeypatch)

    def conflict(*_args, **_kwargs):
        raise task_mutations.tasks.TaskIdConflict("conteúdo privado")

    monkeypatch.setattr(task_mutations.tasks, "add", conflict)
    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert "conteúdo privado" not in response.text
```

- [ ] **Step 2: Run the endpoint tests and confirm route failure**

Run: `python -m pytest tests/test_api_task_mutations.py -q`

Expected: FAIL because `api.task_mutations` and `POST /v1/tasks` do not exist.

- [ ] **Step 3: Implement request and response models plus the router**

```python
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator

from api.models import ApiModel
from api.mutations import NexoMutationError, mutation_lock, require_api_writes
from api.security import require_api_token
from api.sheets import clear_dashboard_cache
from modules import tasks


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/tasks", tags=["tarefas"])


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


@router.post("", response_model=CreateTaskResponse, response_model_by_alias=True)
def create_task(
    payload: CreateTaskRequest,
    request: Request,
    _token=Depends(require_api_token),
    _writes=Depends(require_api_writes),
):
    try:
        with mutation_lock():
            record, created = tasks.add(
                payload.title,
                payload.category,
                payload.date,
                item_id=str(payload.id),
            )
        clear_dashboard_cache()
    except tasks.TaskIdConflict as error:
        raise NexoMutationError(
            409,
            "idempotency_conflict",
            "Esta operação já foi usada com outro conteúdo.",
        ) from error
    except NexoMutationError:
        raise
    except Exception as error:
        logger.exception(
            "Falha ao criar tarefa. operation_id=%s",
            request.state.operation_id,
        )
        raise NexoMutationError(
            503,
            "write_failed",
            "Não foi possível salvar a tarefa agora.",
        ) from error

    return {
        "operation_id": request.state.operation_id,
        "created": created,
        "task": {
            "id": str(record["id"]),
            "date": str(record["data"]),
            "title": str(record["tarefa"]),
            "category": str(record["categoria"]),
            "completed": str(record["status"]).lower() in {"concluída", "concluida"},
        },
    }
```

Import the router in `api/main.py` and register it once with `app.include_router(task_mutations_router)`.

- [ ] **Step 4: Add invalid-input and identical-retry tests**

Add the following cases to `tests/test_api_task_mutations.py`:

```python
def test_task_creation_rejects_empty_title_before_domain(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        task_mutations.tasks,
        "add",
        lambda *_args, **_kwargs: pytest.fail("invalid input must not reach domain"),
    )
    response = client.post(
        "/v1/tasks",
        json={**PAYLOAD, "title": "   "},
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_task_creation_reports_identical_retry(monkeypatch):
    enable_mutations(monkeypatch)
    monkeypatch.setattr(
        task_mutations.tasks,
        "add",
        lambda title, category, target, item_id: ({
            "id": item_id,
            "data": str(target),
            "tarefa": title,
            "categoria": category,
            "status": "Pendente",
        }, False),
    )
    monkeypatch.setattr(task_mutations, "clear_dashboard_cache", lambda: None)

    response = client.post("/v1/tasks", json=PAYLOAD, headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["created"] is False


def test_task_creation_still_requires_correct_server_token(monkeypatch):
    enable_mutations(monkeypatch)
    response = client.post(
        "/v1/tasks",
        json=PAYLOAD,
        headers={"X-Nexo-Token": "wrong"},
    )

    assert response.status_code == 401
```

Import `pytest` at the top of the test module.

- [ ] **Step 5: Run API and domain suites**

Run: `python -m pytest tests/test_api_task_mutations.py tests/test_api_mutations.py tests/test_api_main.py tests/test_tasks.py -q`

Expected: PASS with no Google credentials and no network calls.

- [ ] **Step 6: Commit Task 6**

```bash
git add api/task_mutations.py api/main.py tests/test_api_task_mutations.py
git commit -m "feat: adicionar criacao protegida de tarefa"
```

### Task 7: GitHub authentication and authorization in Next.js

**Files:**
- Create: `web/src/auth.ts`
- Create: `web/src/proxy.ts`
- Create: `web/src/app/api/auth/[...nextauth]/route.ts`
- Create: `web/src/lib/auth-policy.ts`
- Create: `web/src/lib/auth-policy.test.ts`
- Create: `web/src/lib/auth-guard.ts`
- Create: `web/src/types/next-auth.d.ts`
- Create: `web/src/app/entrar/page.tsx`
- Create: `web/src/app/acesso-negado/page.tsx`
- Create: `web/src/components/auth-shell.module.css`
- Create: `web/src/test/setup.ts`
- Modify: `web/src/lib/nexo-api.ts:1-25`
- Modify: `web/src/components/app-shell.tsx:1-104`
- Modify: `web/src/components/app-shell.module.css`
- Modify: `web/vitest.config.ts:13-15`
- Modify: `web/package.json`
- Modify: `web/pnpm-lock.yaml`

**Interfaces:**
- Produces: `isAllowedGitHubIdentity(identity, allowedId) -> boolean`
- Produces: `requireAuthorizedSession() -> Promise<Session>`
- Produces: Auth.js `auth`, `handlers`, `signIn`, `signOut`
- Changes: every `fetchNexoApi()` call revalidates the server session before reading data
- Constraint: authorization fails closed when `NEXO_ALLOWED_GITHUB_ID` is absent

- [ ] **Step 1: Install exact authentication dependency**

Run from `web/`: `pnpm add next-auth@5.0.0-beta.32`

Expected: `package.json` and `pnpm-lock.yaml` change; no other files change.

- [ ] **Step 2: Write failing pure authorization tests**

```typescript
import { describe, expect, it } from "vitest";

import { isAllowedGitHubIdentity } from "./auth-policy";

describe("isAllowedGitHubIdentity", () => {
  it("autoriza somente o ID numérico configurado", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "12345", githubLogin: "DaviFreitas-dev" },
        "12345",
      ),
    ).toBe(true);
  });

  it("recusa o mesmo login com outro ID", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "99999", githubLogin: "DaviFreitas-dev" },
        "12345",
      ),
    ).toBe(false);
  });

  it("falha fechado sem ID configurado", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "12345", githubLogin: "DaviFreitas-dev" },
        undefined,
      ),
    ).toBe(false);
  });

  it("recusa uma configuração que não seja um ID numérico", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "DaviFreitas-dev", githubLogin: "DaviFreitas-dev" },
        "DaviFreitas-dev",
      ),
    ).toBe(false);
  });
});
```

- [ ] **Step 3: Run the policy test and confirm the missing module failure**

Run from `web/`: `pnpm test -- src/lib/auth-policy.test.ts`

Expected: FAIL because `auth-policy.ts` does not exist.

- [ ] **Step 4: Implement the pure policy and Auth.js JWT fields**

`web/src/lib/auth-policy.ts`:

```typescript
export type GitHubIdentity = {
  githubId?: string | null;
  githubLogin?: string | null;
};

export function isAllowedGitHubIdentity(
  identity: GitHubIdentity | null | undefined,
  allowedId: string | undefined,
): boolean {
  const expected = allowedId?.trim();
  return Boolean(expected && /^\d+$/.test(expected) && identity?.githubId === expected);
}
```

`web/src/types/next-auth.d.ts`:

```typescript
import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: DefaultSession["user"] & {
      githubId: string;
      githubLogin: string;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    githubId?: string;
    githubLogin?: string;
  }
}
```

- [ ] **Step 5: Configure GitHub, stateless sessions and fail-closed callbacks**

Create `web/src/auth.ts` using the official Auth.js v5 exports:

```typescript
import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

import { isAllowedGitHubIdentity } from "@/lib/auth-policy";

type GitHubProfile = {
  id?: number | string;
  login?: string;
};

export const { auth, handlers, signIn, signOut } = NextAuth({
  providers: [GitHub],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/entrar",
    error: "/acesso-negado",
  },
  callbacks: {
    signIn({ account, profile }) {
      const github = profile as GitHubProfile | undefined;
      return isAllowedGitHubIdentity(
        {
          githubId: account?.providerAccountId ?? String(github?.id ?? ""),
          githubLogin: github?.login ?? "",
        },
        process.env.NEXO_ALLOWED_GITHUB_ID,
      );
    },
    jwt({ token, account, profile }) {
      if (account?.providerAccountId) {
        token.githubId = account.providerAccountId;
      }
      const github = profile as GitHubProfile | undefined;
      if (github?.login) {
        token.githubLogin = github.login;
      }
      return token;
    },
    session({ session, token }) {
      session.user.githubId = token.githubId ?? "";
      session.user.githubLogin = token.githubLogin ?? "";
      return session;
    },
    authorized({ auth: session }) {
      return isAllowedGitHubIdentity(
        session?.user,
        process.env.NEXO_ALLOWED_GITHUB_ID,
      );
    },
  },
});
```

Do not authorize by email, display name or login alone.

- [ ] **Step 6: Add Auth.js route handler and Next.js 16 proxy**

`web/src/app/api/auth/[...nextauth]/route.ts`:

```typescript
import { handlers } from "@/auth";

export const { GET, POST } = handlers;
```

`web/src/proxy.ts`:

```typescript
export { auth as proxy } from "@/auth";

export const config = {
  matcher: [
    "/((?!api/auth|api/health|_next/static|_next/image|favicon.ico|entrar|acesso-negado).*)",
  ],
};
```

- [ ] **Step 7: Recheck authorization beside server-side data access**

Create `web/src/lib/auth-guard.ts`:

```typescript
import "server-only";

import { auth } from "@/auth";
import { isAllowedGitHubIdentity } from "@/lib/auth-policy";


export async function requireAuthorizedSession() {
  const session = await auth();
  if (
    !session?.user ||
    !isAllowedGitHubIdentity(session.user, process.env.NEXO_ALLOWED_GITHUB_ID)
  ) {
    throw new Error("Acesso não autorizado.");
  }
  return session;
}
```

Call `await requireAuthorizedSession()` as the first line of `fetchNexoApi()`.

Add `web/src/test/setup.ts` with a default authorized mock for existing source tests:

```typescript
import { vi } from "vitest";

vi.mock("@/lib/auth-guard", () => ({
  requireAuthorizedSession: vi.fn().mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  }),
}));
```

Register it as `setupFiles: ["./src/test/setup.ts"]` in `vitest.config.ts`.

- [ ] **Step 8: Add natural login, refusal and logout UI**

Create `web/src/app/entrar/page.tsx`:

```tsx
import { signIn } from "@/auth";
import styles from "@/components/auth-shell.module.css";

export default function SignInPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <span className={styles.brand}>NEXO</span>
        <h1>Acesso pessoal</h1>
        <p>Entre com sua conta GitHub para abrir o NEXO.</p>
        <form
          action={async () => {
            "use server";
            await signIn("github", { redirectTo: "/" });
          }}
        >
          <button type="submit">Entrar com GitHub</button>
        </form>
      </section>
    </main>
  );
}
```

Create `web/src/app/acesso-negado/page.tsx`:

```tsx
import Link from "next/link";

import styles from "@/components/auth-shell.module.css";

export default function AccessDeniedPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <span className={styles.brand}>NEXO</span>
        <h1>Acesso não autorizado</h1>
        <p>Esta conta não tem acesso ao NEXO.</p>
        <Link href="/entrar">Voltar ao login</Link>
      </section>
    </main>
  );
}
```

In `AppShell`, import `signOut` and add this form after the navigation:

```tsx
<form
  action={async () => {
    "use server";
    await signOut({ redirectTo: "/entrar" });
  }}
  className={styles.signOutForm}
>
  <button className={styles.signOutButton} type="submit">Sair</button>
</form>
```

`auth-shell.module.css` owns `.page`, `.card` and `.brand`; `app-shell.module.css` owns `.signOutForm` and `.signOutButton`. Use existing dark CSS variables, a visible `:focus-visible` outline and transitions of 180 ms inside `@media (prefers-reduced-motion: no-preference)`. Do not add emojis, neon or a new gradient.

- [ ] **Step 9: Run web tests and compilation gates**

Run from `web/`: `pnpm test`

Run from `web/`: `pnpm lint`

Run from `web/`: `pnpm typecheck`

Run from `web/`: `pnpm build`

Expected: all commands succeed; build includes `/api/auth/[...nextauth]`, `/entrar` and `/acesso-negado`.

- [ ] **Step 10: Commit Task 7**

```bash
git add web/package.json web/pnpm-lock.yaml web/vitest.config.ts web/src/auth.ts web/src/proxy.ts web/src/types/next-auth.d.ts web/src/lib/auth-policy.ts web/src/lib/auth-policy.test.ts web/src/lib/auth-guard.ts web/src/lib/nexo-api.ts web/src/test/setup.ts web/src/app/api/auth web/src/app/entrar web/src/app/acesso-negado web/src/components/auth-shell.module.css web/src/components/app-shell.tsx web/src/components/app-shell.module.css
git commit -m "feat(web): restringir acesso pela conta GitHub"
```

### Task 8: Server Action and guarded task form

**Files:**
- Create: `web/src/lib/write-policy.ts`
- Create: `web/src/lib/write-policy.test.ts`
- Create: `web/src/app/tarefas/actions.ts`
- Create: `web/src/app/tarefas/actions.test.ts`
- Create: `web/src/components/task-create-form.tsx`
- Modify: `web/src/lib/nexo-api.ts`
- Modify: `web/src/components/tasks-workspace.tsx:1-58`
- Modify: `web/src/components/personal-workspace.module.css:133-230`
- Modify: `web/src/app/tarefas/page.tsx:1-20`
- Modify: `web/package.json`
- Modify: `web/pnpm-lock.yaml`

**Interfaces:**
- Produces: `mutationsUiEnabled() -> boolean`, default false
- Produces: `requestNexoApi<T>(path, init) -> Promise<T>`
- Produces: `createTaskAction(previousState, formData) -> Promise<CreateTaskState>`
- UI receives: `canMutate: boolean` and `initialItemId: string`
- Constraint: UI visibility is convenience only; Auth.js and FastAPI gates remain authoritative

- [ ] **Step 1: Install exact server-validation dependency**

Run from `web/`: `pnpm add zod@4.4.3`

Expected: only package manifest and lockfile change.

- [ ] **Step 2: Write failing write-policy tests**

```typescript
import { afterEach, describe, expect, it } from "vitest";

import { mutationsUiEnabled } from "./write-policy";

afterEach(() => {
  delete process.env.NEXO_WEB_WRITES_ENABLED;
});

describe("mutationsUiEnabled", () => {
  it("fica desativado por padrão", () => {
    expect(mutationsUiEnabled()).toBe(false);
  });

  it("aceita somente true explícito", () => {
    process.env.NEXO_WEB_WRITES_ENABLED = "true";
    expect(mutationsUiEnabled()).toBe(true);
  });
});
```

- [ ] **Step 3: Implement the server-only UI flag**

```typescript
import "server-only";

export function mutationsUiEnabled(): boolean {
  return process.env.NEXO_WEB_WRITES_ENABLED?.trim().toLowerCase() === "true";
}
```

Run from `web/`: `pnpm test -- src/lib/write-policy.test.ts`

Expected: PASS.

- [ ] **Step 4: Write failing API-client error tests**

Create `web/src/lib/nexo-api.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";

import { NexoApiError, requestNexoApi } from "./nexo-api";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("requestNexoApi", () => {
  it("traduz um conflito seguro da API", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        error: {
          code: "idempotency_conflict",
          message: "Esta operação já foi usada com outro conteúdo.",
          operationId: "operation-1",
        },
      }), { status: 409 }),
    ));

    const error = await requestNexoApi("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({ id: "task-1" }),
    }).catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(NexoApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "idempotency_conflict",
      operationId: "operation-1",
    });
  });

  it("mantém token e JSON somente na chamada do servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestNexoApi("/v1/tasks", { method: "POST", body: "{}" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/tasks",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-Nexo-Token": "server-test",
        }),
      }),
    );
  });
});
```

- [ ] **Step 5: Generalize the server-only API client**

Keep `fetchNexoApi(path)` for existing reads and add:

```typescript
export class NexoApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly operationId?: string,
  ) {
    super(message);
  }
}

export async function requestNexoApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  await requireAuthorizedSession();
  const baseUrl = process.env.NEXO_API_URL?.replace(/\/$/, "");
  const apiToken = process.env.NEXO_API_TOKEN;
  if (!baseUrl || !apiToken) {
    throw new Error("A comunicação segura do NEXO não foi configurada.");
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Nexo-Token": apiToken,
      ...init.headers,
    },
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    const problem = readApiProblem(payload);
    throw new NexoApiError(
      response.status,
      problem.code,
      problem.message,
      problem.operationId,
    );
  }
  return payload as T;
}
```

Implement `readApiProblem()` as a defensive type guard that defaults to `code="unexpected_api_error"` and `message="Não foi possível concluir a operação."`. Make `fetchNexoApi()` preserve its current `null` demo behavior when `NEXO_API_URL` is absent, while still calling `requireAuthorizedSession()` before returning personal API data.

Use this exact parser:

```typescript
type ApiProblem = { code: string; message: string; operationId?: string };

function readApiProblem(payload: unknown): ApiProblem {
  if (!payload || typeof payload !== "object" || !("error" in payload)) {
    return {
      code: "unexpected_api_error",
      message: "Não foi possível concluir a operação.",
    };
  }
  const error = payload.error;
  if (!error || typeof error !== "object") {
    return {
      code: "unexpected_api_error",
      message: "Não foi possível concluir a operação.",
    };
  }
  return {
    code: typeof error.code === "string" ? error.code : "unexpected_api_error",
    message: typeof error.message === "string"
      ? error.message
      : "Não foi possível concluir a operação.",
    operationId: typeof error.operationId === "string"
      ? error.operationId
      : undefined,
  };
}
```

- [ ] **Step 6: Write failing Server Action tests**

Start `actions.test.ts` with deterministic mocks:

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import { createTaskAction, initialCreateTaskState } from "./actions";

const { revalidatePath } = vi.hoisted(() => ({ revalidatePath: vi.fn() }));

vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/nexo-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/nexo-api")>();
  return { ...original, requestNexoApi: vi.fn() };
});

function validForm() {
  const form = new FormData();
  form.set("itemId", "0f3ac9b0-5779-40ce-834d-40a8657684af");
  form.set("title", "  Revisar matemática  ");
  form.set("category", "  Estudo  ");
  form.set("date", "2026-08-23");
  return form;
}

beforeEach(() => {
  vi.mocked(requestNexoApi).mockReset();
  revalidatePath.mockReset();
});
```

Use this state contract in `actions.ts`:

```typescript
export type CreateTaskState = {
  status: "idle" | "error" | "success";
  message: string;
  fieldErrors: Partial<Record<"title" | "category" | "date", string[]>>;
  submittedItemId: string | null;
  nextItemId: string | null;
};
```

Add these tests:

```typescript
describe("createTaskAction", () => {
  it("preserva o formulário quando o título está vazio", async () => {
    const form = validForm();
    form.set("title", "   ");

    const state = await createTaskAction(initialCreateTaskState, form);

    expect(state.status).toBe("error");
    expect(state.fieldErrors.title).toBeDefined();
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("envia valores normalizados e revalida depois do sucesso", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({ created: true });

    const state = await createTaskAction(initialCreateTaskState, validForm());

    expect(requestNexoApi).toHaveBeenCalledWith("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        id: "0f3ac9b0-5779-40ce-834d-40a8657684af",
        date: "2026-08-23",
        title: "Revisar matemática",
        category: "Estudo",
      }),
    });
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
    expect(state.status).toBe("success");
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("traduz bloqueio de escrita sem perder o ID enviado", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(503, "writes_disabled", "blocked", "operation-1"),
    );

    const state = await createTaskAction(initialCreateTaskState, validForm());

    expect(state.message).toBe("As alterações ainda não estão disponíveis nesta versão.");
    expect(state.submittedItemId).toBe("0f3ac9b0-5779-40ce-834d-40a8657684af");
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});
```

Add this conflict assertion:

```typescript
it("traduz conflito de idempotência", async () => {
  vi.mocked(requestNexoApi).mockRejectedValue(
    new NexoApiError(409, "idempotency_conflict", "conflict", "operation-2"),
  );

  const state = await createTaskAction(initialCreateTaskState, validForm());

  expect(state.message).toBe(
    "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente.",
  );
  expect(state.submittedItemId).toBe("0f3ac9b0-5779-40ce-834d-40a8657684af");
  expect(revalidatePath).not.toHaveBeenCalled();
});
```

- [ ] **Step 7: Implement Zod validation and the authenticated Server Action**

Create `web/src/app/tarefas/actions.ts`:

```typescript
"use server";

import { randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import * as z from "zod";

import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";

const CreateTaskSchema = z.object({
  itemId: z.uuid({ error: "O identificador do formulário é inválido." }),
  title: z.string().trim().min(1, "Informe a tarefa.").max(160, "Use até 160 caracteres."),
  category: z.string().trim().min(1, "Informe a categoria.").max(40, "Use até 40 caracteres."),
  date: z.iso.date({ error: "Informe uma data válida." }),
});

export type CreateTaskState = {
  status: "idle" | "error" | "success";
  message: string;
  fieldErrors: Partial<Record<"title" | "category" | "date", string[]>>;
  submittedItemId: string | null;
  nextItemId: string | null;
};

export const initialCreateTaskState: CreateTaskState = {
  status: "idle",
  message: "",
  fieldErrors: {},
  submittedItemId: null,
  nextItemId: null,
};

export async function createTaskAction(
  _previous: CreateTaskState,
  formData: FormData,
): Promise<CreateTaskState> {
  const parsed = CreateTaskSchema.safeParse({
    itemId: formData.get("itemId"),
    title: formData.get("title"),
    category: formData.get("category"),
    date: formData.get("date"),
  });
  if (!parsed.success) {
    const errors = z.flattenError(parsed.error).fieldErrors;
    return {
      status: "error",
      message: "Revise os campos indicados.",
      fieldErrors: {
        title: errors.title,
        category: errors.category,
        date: errors.date,
      },
      submittedItemId: String(formData.get("itemId") ?? "") || null,
      nextItemId: null,
    };
  }

  try {
    await requestNexoApi("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        id: parsed.data.itemId,
        date: parsed.data.date,
        title: parsed.data.title,
        category: parsed.data.category,
      }),
    });
  } catch (error) {
    const message = error instanceof NexoApiError && error.code === "writes_disabled"
      ? "As alterações ainda não estão disponíveis nesta versão."
      : error instanceof NexoApiError && error.code === "idempotency_conflict"
        ? "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente."
        : "Não foi possível adicionar a tarefa agora.";
    return {
      status: "error",
      message,
      fieldErrors: {},
      submittedItemId: parsed.data.itemId,
      nextItemId: null,
    };
  }

  revalidatePath("/tarefas");
  revalidatePath("/");
  return {
    status: "success",
    message: "Tarefa adicionada.",
    fieldErrors: {},
    submittedItemId: parsed.data.itemId,
    nextItemId: randomUUID(),
  };
}
```

- [ ] **Step 8: Add the client form with stable retry ID**

Create `web/src/components/task-create-form.tsx` with this state flow:

```tsx
"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import {
  createTaskAction,
  initialCreateTaskState,
} from "@/app/tarefas/actions";
import styles from "./personal-workspace.module.css";

type TaskCreateFormProps = {
  initialItemId: string;
  selectedDate: string;
};

export function TaskCreateForm({ initialItemId, selectedDate }: TaskCreateFormProps) {
  const [itemId, setItemId] = useState(initialItemId);
  const [state, action, pending] = useActionState(
    createTaskAction,
    initialCreateTaskState,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (
      state.status === "success" &&
      state.submittedItemId === itemId &&
      state.nextItemId
    ) {
      formRef.current?.reset();
      setItemId(state.nextItemId);
    }
  }, [itemId, state]);

  return (
    <form action={action} className={styles.createForm} ref={formRef}>
      <div className={styles.sectionHeading}><h2>Nova tarefa</h2></div>
      <input name="itemId" type="hidden" value={itemId} />
      <input name="date" type="hidden" value={selectedDate} />
      <label>
        <span>O que precisa ser feito?</span>
        <input disabled={pending} maxLength={160} name="title" required />
        {state.fieldErrors.title?.map((error) => <small key={error}>{error}</small>)}
      </label>
      <label>
        <span>Categoria</span>
        <input defaultValue="Geral" disabled={pending} maxLength={40} name="category" required />
        {state.fieldErrors.category?.map((error) => <small key={error}>{error}</small>)}
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Salvando..." : "Adicionar tarefa"}
      </button>
      <p aria-live="polite" className={styles.formMessage}>{state.message}</p>
    </form>
  );
}
```

The hidden ID changes only after a confirmed success. Uncontrolled title and category inputs therefore retain their values after validation or API errors.

Visible copy:

- heading: “Nova tarefa”;
- title label: “O que precisa ser feito?”;
- category label: “Categoria”;
- submit idle: “Adicionar tarefa”;
- submit pending: “Salvando...”;
- success: “Tarefa adicionada.”

- [ ] **Step 9: Gate the form in the server page**

In `web/src/app/tarefas/page.tsx`, create `initialItemId` with `randomUUID()` from `node:crypto` and pass:

```typescript
canMutate={result.source === "api" && mutationsUiEnabled()}
initialItemId={randomUUID()}
```

Render `TaskCreateForm` in `TasksWorkspace` only when `canMutate` is true. Do not show a disabled or misleading edit button in demo/read-only mode.

- [ ] **Step 10: Style form states and reduced motion**

Add these focused classes to `personal-workspace.module.css` and align values with existing tokens:

```css
.createForm {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(160px, 0.35fr) auto;
  gap: 12px;
  margin-top: 30px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.createForm .sectionHeading { grid-column: 1 / -1; margin-bottom: 0; }
.createForm label { display: grid; gap: 7px; color: var(--color-muted); font-size: 0.64rem; }
.createForm input {
  min-height: 40px;
  padding: 0 11px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  color: var(--color-text);
  background: var(--color-surface-raised);
}
.createForm input:focus-visible,
.createForm button:focus-visible { outline: 2px solid var(--color-accent-soft); outline-offset: 2px; }
.createForm button { min-height: 40px; align-self: end; }
.createForm button:disabled { cursor: wait; opacity: 0.58; }
.createForm small { color: #d99a9a; }
.formMessage { grid-column: 1 / -1; min-height: 1rem; margin: 0; color: var(--color-muted); font-size: 0.64rem; }

@media (prefers-reduced-motion: no-preference) {
  .createForm input,
  .createForm button { transition: border-color 180ms ease, opacity 180ms ease; }
}

@media (max-width: 680px) {
  .createForm { grid-template-columns: 1fr; }
  .createForm .sectionHeading,
  .formMessage { grid-column: 1; }
}
```

Do not add emojis, neon or a new gradient.

- [ ] **Step 11: Run focused and complete web gates**

Run from `web/`: `pnpm test -- src/lib/nexo-api.test.ts src/lib/write-policy.test.ts src/app/tarefas/actions.test.ts`

Run from `web/`: `pnpm test && pnpm lint && pnpm typecheck && pnpm build`

Expected: all commands succeed with both `NEXO_WEB_WRITES_ENABLED` and live API writes absent.

- [ ] **Step 12: Commit Task 8**

```bash
git add web/package.json web/pnpm-lock.yaml web/src/lib/nexo-api.ts web/src/lib/nexo-api.test.ts web/src/lib/write-policy.ts web/src/lib/write-policy.test.ts web/src/app/tarefas/actions.ts web/src/app/tarefas/actions.test.ts web/src/app/tarefas/page.tsx web/src/components/task-create-form.tsx web/src/components/tasks-workspace.tsx web/src/components/personal-workspace.module.css
git commit -m "feat(web): preparar criacao segura de tarefas"
```

### Task 9: Configuration docs and complete verification

**Files:**
- Modify: `api/.env.example`
- Modify: `api/README.md`
- Modify: `web/.env.example`
- Modify: `web/README.md`
- Modify: `.gitignore` only if a new local Auth.js file is not already covered

**Interfaces:**
- Documents Vercel names: `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, `AUTH_SECRET`, `NEXO_ALLOWED_GITHUB_ID`, `NEXO_API_URL`, `NEXO_API_TOKEN`, `NEXO_WEB_WRITES_ENABLED`
- Documents Render names: `NEXO_API_TOKEN`, `GSHEETS_SERVICE_ACCOUNT_JSON`, `NEXO_API_WRITES_ENABLED`, `NEXO_TIMEZONE`
- Documents GitHub callback: `/api/auth/callback/github`
- Keeps every example value empty or fictitious

- [ ] **Step 1: Update environment examples with closed gates**

`api/.env.example` must contain:

```dotenv
NEXO_API_TOKEN=
GSHEETS_SERVICE_ACCOUNT_JSON=
NEXO_TIMEZONE=America/Fortaleza
NEXO_API_WRITES_ENABLED=false
```

`web/.env.example` must contain:

```dotenv
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
AUTH_SECRET=
NEXO_ALLOWED_GITHUB_ID=
NEXO_API_URL=http://127.0.0.1:8000
NEXO_API_TOKEN=
NEXO_WEB_WRITES_ENABLED=false
```

- [ ] **Step 2: Document local login and write-safety behavior**

In `web/README.md`, document the GitHub OAuth callback as `http://localhost:3000/api/auth/callback/github` locally and `https://<dominio>/api/auth/callback/github` in Vercel. State that `NEXO_ALLOWED_GITHUB_ID` is numeric, not the login, and that neither write flag should be enabled in production during this delivery.

In `api/README.md`, replace “API somente de leitura” with “leitura e fundação de mutações bloqueadas por padrão”, list `POST /v1/tasks`, and state that the endpoint requires both the server token and explicit write gate.

Document the first production start command with one worker:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1
```

State that increasing workers or Render instances is forbidden until the project has a distributed mutation lock.

- [ ] **Step 3: Run the complete Python verification**

Run: `python -m pytest -q`

Run: `python -m compileall -q app.py modules api views`

Expected: all tests pass; compileall emits no output.

- [ ] **Step 4: Run the complete web verification**

Run from `web/`: `pnpm test`

Run from `web/`: `pnpm lint`

Run from `web/`: `pnpm typecheck`

Run from `web/`: `pnpm build`

Expected: all commands succeed without real Auth.js or Sheets secrets.

- [ ] **Step 5: Verify secret hygiene and exact diff**

Run:

```bash
git diff --check
git status -sb
git diff --stat main...HEAD
git diff main...HEAD -- . ':!web/pnpm-lock.yaml'
```

Run a tracked-file scan:

```bash
git grep -n -I -E 'BEGIN PRIVATE KEY|private_key_id|ghp_[A-Za-z0-9]|github_pat_' -- . ':!docs/superpowers/plans/*'
```

Expected: the secret scan returns no matches; only planned source, tests, dependency lock and documentation appear in the diff.

- [ ] **Step 6: Confirm production gates remain closed**

Check the final code and examples for these defaults:

```text
NEXO_API_WRITES_ENABLED missing or false -> FastAPI returns writes_disabled
NEXO_WEB_WRITES_ENABLED missing or false -> no task form is rendered
```

Do not call `scripts/backfill_missing_ids.py --apply-plan` and do not send a live `POST /v1/tasks`.

- [ ] **Step 7: Commit Task 9**

```bash
git add api/.env.example api/README.md web/.env.example web/README.md .gitignore
git commit -m "docs: configurar fundacao segura de escritas"
```

## Completion Criteria for Delivery 1

- GitHub authentication is fail-closed and authorizes only the configured numeric account ID.
- Every protected data read and task Server Action rechecks the session on the server.
- No API or Google secret is present in browser bundles or `NEXT_PUBLIC_` variables.
- `modules.database` imports and works without a Streamlit runtime context.
- Read cache retains the 15-second TTL and returns copies.
- `POST /v1/tasks` requires token plus explicit write gate.
- Repeating the same task UUID and content does not append another row.
- Reusing the UUID with different content returns a safe 409 conflict.
- API cache clears only after a confirmed domain result.
- The ID backfill is dry-run by default and has not been executed live.
- The task form is absent unless its separate server-side UI flag is explicitly enabled.
- Python and web verification gates all pass.
- No operation in this delivery writes to the real spreadsheet.

## Primary References

- [Auth.js installation for Next.js](https://authjs.dev/getting-started/installation?framework=Next.js)
- [Auth.js GitHub provider](https://authjs.dev/getting-started/providers/github)
- Local Next.js 16 guide: `web/node_modules/next/dist/docs/01-app/02-guides/authentication.md`
- Local Next.js 16 Server Actions guide: `web/node_modules/next/dist/docs/01-app/02-guides/server-actions.md`
- Local Next.js 16 Proxy guide: `web/node_modules/next/dist/docs/01-app/01-getting-started/16-proxy.md`
