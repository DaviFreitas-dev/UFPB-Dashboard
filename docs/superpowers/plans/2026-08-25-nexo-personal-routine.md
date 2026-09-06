# NEXO Personal Routine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe, idempotent Next.js write flows for tasks, custom routine items, habits, reading and physical activity, including matching actions on Today, while keeping production write gates disabled.

**Architecture:** Keep Python domain modules as the single source of business and XP rules. Next.js Server Actions validate authenticated form submissions and call resource-specific FastAPI routes guarded by the existing private token, write gate and global mutation lock; successful responses invalidate precise Python caches and revalidate only consuming Next.js routes.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, gspread, pytest, Next.js 16, React 19, TypeScript 6, Zod 4, Vitest, Testing Library, jsdom, pnpm.

**Spec:** `docs/superpowers/specs/2026-08-25-nexo-personal-routine-design.md`

## Global Constraints

- `NEXO_API_WRITES_ENABLED` remains `false` outside isolated automated tests.
- `NEXO_WEB_WRITES_ENABLED` remains `false` outside isolated automated tests.
- The Streamlit application remains the operational writer until Delivery 4.
- Never execute the ID backfill against the real spreadsheet in this delivery.
- Never send automated tests to the real Google Sheets workbook.
- Never expose `NEXO_API_TOKEN`, Google credentials or internal storage errors to the browser or logs.
- All creates use stable IDs; all updates use desired state instead of blind toggles.
- XP uses the existing event keys and is never granted twice for the same event.
- Legacy rows remain readable; rows without persistent IDs are shown but are not mutable.
- `AgendaSemanal` and `AgendaCheckins` remain read-only until Delivery 3.
- Preserve `views/` and manual navigation; do not create or restore `pages/`.
- UI copy stays short and natural in Portuguese, without decorative emoji; the approved sequence indicator remains.
- Mutations remain safe with one API process and the existing process-local global lock.
- On this Windows host, prepend `C:\Users\david\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin` to `PATH` and invoke `C:\Users\david\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd` when `node` or `pnpm` is not available normally.

---

## Planned file structure

### Shared API boundary

- `api/mutation_http.py`: reusable guarded route, token dependency, body validation and common mutation error response models.
- `api/mutation_audit.py`: structured mutation logging that accepts only identifiers and sheet names.
- `api/mutations.py`: existing write gate, request ID middleware, exception handler and global lock.
- `api/*_mutations.py`: one router per domain; no generic command endpoint.

### Domain rules

- `modules/tasks.py`, `modules/routine.py`, `modules/habits.py`, `modules/reading.py`, `modules/activity.py`: idempotent creation, desired-state updates, safe deletion and XP rules.
- `modules/database.py`: existing point writes and per-sheet record cache; no broad rewrite of sheets.
- `api/sheets.py`: invalidation of the aggregate read cache after confirmed mutations.

### Web actions and controls

- `web/src/actions/mutation-state.ts`: shared serializable states and safe error-message mapping.
- `web/src/actions/{tasks,routine,habits,reading,activity}.ts`: authenticated Server Actions by domain.
- `web/src/lib/personal-mutation-contracts.ts`: Zod response schemas matching FastAPI.
- `web/src/components/personal-actions/`: focused client forms and desired-state controls reused by domain pages and Today.
- Existing workspace components remain responsible for layout and receive `canMutate` plus stable initial IDs from their server pages.

### Tests

- Python domain tests stay in `tests/test_<domain>.py`.
- FastAPI route tests stay in `tests/test_api_<domain>_mutations.py`.
- Server Action tests stay beside each action module.
- DOM interaction tests stay beside components and use `// @vitest-environment jsdom`.

---

### Task 1: Extract the reusable mutation HTTP and audit boundary

**Files:**
- Create: `api/mutation_http.py`
- Create: `api/mutation_audit.py`
- Create: `tests/test_api_mutation_http.py`
- Modify: `api/task_mutations.py`
- Modify: `tests/test_api_task_mutations.py`
- Modify: `api/main.py`

**Interfaces:**
- Produces: `MutationApiRoute(APIRoute)`.
- Produces: `require_mutation_api_token(x_nexo_token: str | None) -> None`.
- Produces: `validate_json_body(request: Request, model: type[ApiModel]) -> ApiModel`.
- Produces: `MutationError` and `MutationErrorResponse` Pydantic models.
- Produces: `log_mutation(request, *, domain: str, resource_id: str, route: str, worksheets: tuple[str, ...], outcome: str, status_code: int, started_at: float) -> None`.
- Preserves: authentication and the write gate run before JSON decoding or Pydantic validation.

- [ ] **Step 1: Write failing tests for the reusable guards and safe audit event**

```python
def test_guarded_route_checks_token_and_gate_before_json(monkeypatch):
    monkeypatch.setenv("NEXO_API_TOKEN", "server-test")
    monkeypatch.delenv("NEXO_API_WRITES_ENABLED", raising=False)
    response = client.post(
        "/test-mutation",
        content=b"{broken",
        headers={"X-Nexo-Token": "server-test", "X-Request-ID": "guard-1"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "writes_disabled"


def test_audit_event_contains_identifiers_but_not_private_content(caplog):
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
```

- [ ] **Step 2: Run the new boundary tests and confirm RED**

Run: `python -m pytest tests/test_api_mutation_http.py -q`

Expected: FAIL because `api.mutation_http` and `api.mutation_audit` do not exist.

- [ ] **Step 3: Implement the reusable boundary and refactor the existing task POST without changing its contract**

```python
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
                    422, "invalid_request", "Revise os dados enviados."
                ) from error

        return guarded


async def validate_json_body(request: Request, model: type[ApiModel]):
    try:
        return model.model_validate(await request.json())
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
        raise NexoMutationError(
            422, "invalid_request", "Revise os dados enviados."
        ) from error
```

Keep each resource parser explicit so FastAPI evaluates `require_mutation_api_token` and `require_api_writes` before calling `validate_json_body`. Refactor `api/task_mutations.py` to import the common route, models, token dependency, validator and logger. Preserve `/v1/tasks` POST response fields and OpenAPI schemas exactly.

- [ ] **Step 4: Run focused and regression tests**

Run: `python -m pytest tests/test_api_mutation_http.py tests/test_api_task_mutations.py tests/test_api_mutations.py tests/test_api_main.py -q`

Expected: PASS with no changed `/v1/tasks` POST behavior.

- [ ] **Step 5: Commit the shared boundary**

```bash
git add api/mutation_http.py api/mutation_audit.py api/task_mutations.py api/main.py tests/test_api_mutation_http.py tests/test_api_task_mutations.py
git commit -m "refactor(api): compartilhar fronteira de mutacoes"
```

---

### Task 2: Complete the task lifecycle and establish shared web mutation controls

**Files:**
- Modify: `modules/tasks.py`
- Modify: `tests/test_tasks.py`
- Modify: `api/task_mutations.py`
- Modify: `tests/test_api_task_mutations.py`
- Modify: `api/personal.py`
- Modify: `api/workspace_models.py`
- Modify: `tests/test_api_workspaces.py`
- Create: `web/src/actions/mutation-state.ts`
- Create: `web/src/actions/tasks.ts`
- Create: `web/src/actions/tasks.test.ts`
- Remove after state imports migrate: `web/src/app/tarefas/task-create-state.ts`
- Create: `web/src/lib/personal-mutation-contracts.ts`
- Modify: `web/src/lib/personal-workspace.ts`
- Modify: `web/src/lib/personal-workspace.test.ts`
- Create: `web/src/components/personal-actions/mutation-submit-button.tsx`
- Create: `web/src/components/personal-actions/task-controls.tsx`
- Create: `web/src/components/personal-actions/task-controls.test.tsx`
- Modify: `web/src/components/task-create-form.tsx`
- Modify: `web/src/components/tasks-workspace.tsx`
- Modify: `web/src/components/personal-workspace.module.css`
- Modify: `web/src/app/tarefas/page.tsx`
- Remove after imports migrate: `web/src/app/tarefas/actions.ts`
- Remove after tests migrate: `web/src/app/tarefas/actions.test.ts`
- Modify: `web/package.json`
- Modify: `web/pnpm-lock.yaml`
- Modify: `web/vitest.config.ts`
- Modify: `web/src/test/setup.ts`

**Interfaces:**
- Produces: `tasks.set_completed(item_id: str, completed: bool) -> tuple[dict | None, bool]`.
- Preserves: `tasks.toggle(item_id, done)` as a compatibility wrapper for Streamlit.
- Produces: `PATCH /v1/tasks/{task_id}` with `{ "completed": boolean }`.
- Produces: `DELETE /v1/tasks/{task_id}`.
- Produces: `PersonalTask(Task)` with `mutable: bool`; only a non-empty persisted row ID sets it to true.
- Produces: `InlineMutationState = { status, message }` and `CreateMutationState = InlineMutationState & { fieldErrors, submittedItemId, nextItemId }`.
- Produces: `createTaskAction`, `setTaskCompletedAction`, `deleteTaskAction` in `web/src/actions/tasks.ts`.
- Produces: Testing Library plus jsdom for real client interaction tests.

- [ ] **Step 1: Write failing Python tests for desired-state completion and repeated deletion**

```python
def test_set_completed_changes_state_and_awards_xp_once(monkeypatch):
    rows = [{"id": "task-1", "status": "Pendente"}]
    updates, awards = [], []
    monkeypatch.setattr(tasks, "records", lambda _name: rows)
    monkeypatch.setattr(tasks, "update_record", lambda name, item_id, values: updates.append(values) or True)
    monkeypatch.setattr(tasks, "award_xp_once", lambda *args: awards.append(args))

    record, changed = tasks.set_completed("task-1", True)

    assert changed is True
    assert record["status"] == "Concluída"
    assert updates == [{"status": "Concluída"}]
    assert awards == [("task:task-1", 15, "tarefa", "Tarefa concluída")]


def test_set_completed_replay_does_not_write_or_award(monkeypatch):
    monkeypatch.setattr(tasks, "records", lambda _name: [{"id": "task-1", "status": "Concluída"}])
    monkeypatch.setattr(tasks, "update_record", lambda *_args: pytest.fail("must not write"))
    monkeypatch.setattr(tasks, "award_xp_once", lambda *_args: pytest.fail("must not award"))
    assert tasks.set_completed("task-1", True)[1] is False
```

Add API tests that assert token -> gate -> validation -> lock ordering, `record_not_found`, confirmed replay, cache clearing, safe audit logs, and `DELETE` returning `{ operationId, id, deleted }` with `deleted: false` when repeated.

- [ ] **Step 2: Run focused Python tests and confirm RED**

Run: `python -m pytest tests/test_tasks.py tests/test_api_task_mutations.py -q`

Expected: FAIL because `set_completed`, PATCH and DELETE are absent.

- [ ] **Step 3: Implement the Python domain methods and API contracts**

```python
def set_completed(item_id, completed):
    current = next(
        (row for row in records("Tarefas") if str(row.get("id")) == str(item_id)),
        None,
    )
    if current is None:
        return None, False
    target = "Concluída" if completed else "Pendente"
    if current.get("status") == target:
        return {**current, "status": target}, False
    if not update_record("Tarefas", item_id, {"status": target}):
        return None, False
    confirmed = {**current, "status": target}
    if completed:
        award_xp_once(f"task:{item_id}", 15, "tarefa", "Tarefa concluída")
    return confirmed, True
```

Define `SetTaskStateRequest(completed: bool)`, reuse `CreatedTask` as the response task, and return `changed` for PATCH. Execute the module call under `mutation_lock()`, then clear the aggregate dashboard cache. DELETE treats an absent record as a confirmed final state and returns `deleted: false`.

- [ ] **Step 4: Write failing Server Action and DOM interaction tests**

Add `@testing-library/react@16.3.0`, `@testing-library/user-event@14.6.1`, `@testing-library/jest-dom@6.8.0` and `jsdom@26.1.0` as pinned dev dependencies. Import `@testing-library/jest-dom/vitest` from `web/src/test/setup.ts`. Use per-file `// @vitest-environment jsdom` so the existing node tests stay unchanged.

```tsx
// @vitest-environment jsdom
it("bloqueia repetição enquanto a tarefa está sendo atualizada", async () => {
  const user = userEvent.setup();
  render(<TaskControls task={task} canMutate />);
  const button = screen.getByRole("button", { name: "Concluir tarefa" });
  await user.click(button);
  expect(button).toBeDisabled();
  await user.click(button);
  expect(setTaskCompletedAction).toHaveBeenCalledTimes(1);
});
```

Server Action tests must assert session first, web gate before `FormData`, Zod validation, exact API path/body/schema, safe error mapping, response confirmation and revalidation of `/tarefas` plus `/` only after success.

- [ ] **Step 5: Run the web tests and confirm RED**

Run: `cd web && pnpm test -- src/actions/tasks.test.ts src/components/personal-actions/task-controls.test.tsx`

Expected: FAIL because the shared actions, schemas and controls do not exist.

- [ ] **Step 6: Implement shared states, task Server Actions and accessible controls**

```ts
export type InlineMutationState = {
  status: "idle" | "success" | "error";
  message: string;
};

export async function setTaskCompletedAction(
  _state: InlineMutationState,
  formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return writesDisabledState;
  const parsed = TaskStateSchema.safeParse({
    id: formData.get("id"),
    completed: formData.get("completed") === "true",
  });
  if (!parsed.success) return invalidInlineState;
  const response = await requestNexoApi(
    `/v1/tasks/${encodeURIComponent(parsed.data.id)}`,
    { method: "PATCH", body: JSON.stringify({ completed: parsed.data.completed }) },
    TaskStateResponseSchema,
  );
  assertConfirmedTaskState(response, parsed.data);
  revalidatePath("/tarefas");
  revalidatePath("/");
  return { status: "success", message: parsed.data.completed ? "Tarefa concluída." : "Tarefa reaberta." };
}
```

Move the existing create action into `web/src/actions/tasks.ts` without changing its retry semantics. Render controls only when `source === "api"`, the web gate is true and the row has a persistent ID. Use `useActionState`, `useFormStatus`, `aria-live`, visible focus, disabled pending buttons and an inline confirmation before deletion.

- [ ] **Step 7: Run task-domain verification**

Run: `python -m pytest tests/test_tasks.py tests/test_api_task_mutations.py -q`

Run: `cd web && pnpm test -- src/actions/tasks.test.ts src/components/personal-actions/task-controls.test.tsx src/components/task-ui.test.tsx`

Expected: all focused tests PASS.

- [ ] **Step 8: Commit the completed task lifecycle**

```bash
git add modules/tasks.py tests/test_tasks.py api/task_mutations.py api/personal.py api/workspace_models.py tests/test_api_task_mutations.py tests/test_api_workspaces.py web/package.json web/pnpm-lock.yaml web/vitest.config.ts web/src/actions web/src/lib/personal-mutation-contracts.ts web/src/lib/personal-workspace.ts web/src/lib/personal-workspace.test.ts web/src/components web/src/app/tarefas
git commit -m "feat: completar ciclo de tarefas na interface web"
```

---

### Task 3: Add custom routine mutations end to end

**Files:**
- Modify: `modules/routine.py`
- Create: `tests/test_routine.py`
- Create: `api/routine_mutations.py`
- Create: `tests/test_api_routine_mutations.py`
- Modify: `api/main.py`
- Modify: `api/models.py`
- Modify: `api/routine.py`
- Modify: `tests/test_api_routine.py`
- Create: `web/src/actions/routine.ts`
- Create: `web/src/actions/routine.test.ts`
- Modify: `web/src/lib/personal-mutation-contracts.ts`
- Modify: `web/src/lib/routine.ts`
- Create: `web/src/components/personal-actions/routine-controls.tsx`
- Create: `web/src/components/personal-actions/routine-controls.test.tsx`
- Modify: `web/src/components/routine-dashboard.tsx`
- Modify: `web/src/components/routine-dashboard.module.css`
- Modify: `web/src/app/rotina/page.tsx`

**Interfaces:**
- Produces: `RoutineIdConflict`.
- Produces: `routine.add(activity, time_text, target_date=None, item_id=None) -> tuple[dict, bool]`.
- Produces: `routine.set_completed(item_id, completed) -> tuple[dict | None, bool]`.
- Produces: `POST /v1/routine-items`, `PATCH /v1/routine-items/{id}`, `DELETE /v1/routine-items/{id}`.
- Extends: `RoutineItem` with `source_id: str` and `mutable: bool`; fixed items always have `mutable: false` in Delivery 2.

- [ ] **Step 1: Write failing domain and API tests**

```python
def test_add_routine_replays_same_uuid_without_second_append(monkeypatch):
    existing = {"id": "routine-1", "data": "2026-08-25", "hora": "08:30", "atividade": "Dentista", "status": "Pendente"}
    monkeypatch.setattr(routine, "records", lambda _name: [existing])
    monkeypatch.setattr(routine, "append_record", lambda *_args, **_kwargs: pytest.fail("must not append"))
    assert routine.add("Dentista", "08:30", date(2026, 8, 25), item_id="routine-1") == (existing, False)


def test_fixed_agenda_item_is_explicitly_read_only():
    dashboard = build_routine_dashboard(tables_with_fixed_and_custom, date(2026, 8, 25))
    fixed, custom = dashboard.items
    assert fixed.kind == "fixed" and fixed.mutable is False
    assert custom.kind == "custom" and custom.mutable is True
```

API tests cover strict `HH:MM`, trimmed activity up to 160 characters, ISO date, replay/conflict, desired completion, repeated delete, legacy missing ID, lock, cache and safe audit fields.

- [ ] **Step 2: Run focused Python tests and confirm RED**

Run: `python -m pytest tests/test_routine.py tests/test_api_routine.py tests/test_api_routine_mutations.py -q`

Expected: FAIL for absent contracts and fields.

- [ ] **Step 3: Implement the routine domain, API router and read-model identity**

Use `value_input_option="RAW"` for creation. Compare immutable replay fields `id`, `data`, `hora` and `atividade`. The API response item is `{ id, date, time, title, completed }`. Keep `/v1/routine` as GET and use `/v1/routine-items` for mutations to avoid a route collision. Only rows from `Rotina` receive actionable source IDs. A transition to completed calls `award_xp_once("routine:<id>", 10, "rotina", "Compromisso do dia concluído")`; reopening and replays do not award XP.

- [ ] **Step 4: Write failing Server Action and component tests**

```tsx
it("não oferece check-in para um item da semana fixa", () => {
  render(<RoutineControls item={{ ...fixedItem, mutable: false }} canMutate />);
  expect(screen.queryByRole("button", { name: /concluir/i })).not.toBeInTheDocument();
  expect(screen.getByText("Check-in disponível na próxima etapa.")).toBeInTheDocument();
});
```

Test stable UUID retry for creation, normalized `HH:MM`, desired completion, deletion confirmation, failure value preservation, exact revalidation of `/rotina` and `/`, and hidden controls for demo data or a closed gate.

- [ ] **Step 5: Implement routine Server Actions and controls**

Create actions `createRoutineItemAction`, `setRoutineItemCompletedAction` and `deleteRoutineItemAction`. The page generates one initial UUID with `randomUUID()`. The create form uses date from the selected route and retains activity/time/UUID after failure. Custom timeline rows receive the shared pending and error behavior; fixed rows remain visibly read-only.

- [ ] **Step 6: Run focused Python and web verification**

Run: `python -m pytest tests/test_routine.py tests/test_api_routine.py tests/test_api_routine_mutations.py -q`

Run: `cd web && pnpm test -- src/actions/routine.test.ts src/components/personal-actions/routine-controls.test.tsx src/lib/routine.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Commit routine mutations**

```bash
git add modules/routine.py tests/test_routine.py api/routine_mutations.py api/main.py api/models.py api/routine.py tests/test_api_routine.py tests/test_api_routine_mutations.py web/src/actions/routine.ts web/src/actions/routine.test.ts web/src/lib web/src/components/personal-actions/routine-controls.tsx web/src/components/personal-actions/routine-controls.test.tsx web/src/components/routine-dashboard.tsx web/src/components/routine-dashboard.module.css web/src/app/rotina/page.tsx
git commit -m "feat: migrar compromissos avulsos da rotina"
```

---

### Task 4: Make habit reads pure and add habit lifecycle mutations

**Files:**
- Modify: `modules/habits.py`
- Create: `tests/test_habits.py`
- Create: `api/habit_mutations.py`
- Create: `tests/test_api_habit_mutations.py`
- Modify: `api/main.py`
- Modify: `api/personal.py`
- Modify: `api/dashboard.py`
- Modify: `api/models.py`
- Modify: `api/workspace_models.py`
- Modify: `tests/test_api_dashboard.py`
- Modify: `tests/test_api_workspaces.py`
- Create: `web/src/actions/habits.ts`
- Create: `web/src/actions/habits.test.ts`
- Modify: `web/src/lib/personal-mutation-contracts.ts`
- Modify: `web/src/lib/personal-workspace.ts`
- Modify: `web/src/lib/dashboard.ts`
- Create: `web/src/components/personal-actions/habit-controls.tsx`
- Create: `web/src/components/personal-actions/habit-controls.test.tsx`
- Modify: `web/src/components/habits-workspace.tsx`
- Modify: `web/src/components/personal-workspace.module.css`
- Modify: `web/src/app/habitos/page.tsx`

**Interfaces:**
- Produces: `habits.records_for_date(target_date) -> list[dict]` with no writes.
- Produces: `habits.add(name, item_id=None) -> tuple[dict, bool, bool]` where booleans mean `created` and `reactivated`.
- Produces: `habits.set_active(config_id, active) -> tuple[dict | None, bool]`.
- Produces: `habits.set_completed(config_id, target_date, completed) -> tuple[dict | None, bool]`.
- Produces: deterministic UUIDv5 log IDs from the fixed namespace, config ID and ISO date.
- Produces: `POST /v1/habits`, `PATCH /v1/habits/{config_id}`, `PUT /v1/habit-checkins/{config_id}/{date}`.

- [ ] **Step 1: Write failing tests proving reads do not write and check-ins converge**

```python
def test_records_for_date_does_not_create_missing_logs(monkeypatch):
    monkeypatch.setattr(habits, "active_configs", lambda: [{"id": "habit-1", "nome": "Ler", "ativo": "Sim"}])
    monkeypatch.setattr(habits, "records", lambda name: [] if name == "Habitos" else [])
    monkeypatch.setattr(habits, "append_record", lambda *_args, **_kwargs: pytest.fail("read must not write"))
    assert habits.records_for_date(date(2026, 8, 25)) == [{
        "config_id": "habit-1", "log_id": None, "data": "2026-08-25", "habito": "Ler", "feito": "Não"
    }]


def test_first_completion_uses_deterministic_log_and_replay_does_not_award_twice(monkeypatch):
    first, changed = habits.set_completed("habit-1", date(2026, 8, 25), True)
    retry, retry_changed = habits.set_completed("habit-1", date(2026, 8, 25), True)
    assert first["id"] == retry["id"]
    assert changed is True and retry_changed is False
    assert awards == [(f"habit:{first['id']}", 10, "habito", "Hábito concluído")]
```

Also test normalized-name reactivation, duplicate active habit replay, archive history preservation, unchecking a missing log as a no-op, missing configuration, legacy config without ID, lock ordering, cache invalidation of both habit sheets and XP deduplication.

- [ ] **Step 2: Run habit tests and confirm RED**

Run: `python -m pytest tests/test_habits.py tests/test_api_habit_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py -q`

Expected: FAIL because current `today()` writes missing rows and the mutation contracts do not exist.

- [ ] **Step 3: Implement pure reads, deterministic writes and API routes**

```python
_HABIT_LOG_NAMESPACE = UUID("698cd68b-c9a8-4f34-b527-f6809e2d3f10")


def _log_id(config_id, target_date):
    return str(uuid5(_HABIT_LOG_NAMESPACE, f"{config_id}:{target_date.isoformat()}"))
```

Match an existing log by normalized habit name plus date before creating. If completed is false and no log exists, return the confirmed false state without writing. `today()` becomes a compatibility wrapper around `records_for_date(date.today())`. Return both `configId` and nullable `logId` in personal and Today read models; set `mutable: false` when the config lacks a persistent ID.

- [ ] **Step 4: Write failing web action and DOM tests**

Test create/reactivate/archive, date-specific mark/unmark, a missing `logId`, response confirmation, exact page revalidation, closed gates, demo source, pending double-click prevention, natural messages and preservation of the habit name after error.

```tsx
it("mantém o indicador de sequência e confirma o hábito pela configuração", async () => {
  render(<HabitControls habit={{ configId: "habit-1", logId: null, title: "Ler", completed: false, streakDays: 4, mutable: true }} date="2026-08-25" canMutate />);
  expect(screen.getByText("4 dias seguidos")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Marcar Ler" }));
  expect(setHabitCompletedAction).toHaveBeenCalledWith(expect.anything(), expect.any(FormData));
});
```

- [ ] **Step 5: Implement habit Server Actions and workspace controls**

Create `createHabitAction`, `setHabitActiveAction` and `setHabitCompletedAction`. The API generates missing log IDs deterministically; the browser never invents a second identity for the same day. Archive requires inline confirmation. The page renders an unavailable explanation for legacy configs without ID and never removes their history from the read view.

- [ ] **Step 6: Run focused verification**

Run: `python -m pytest tests/test_habits.py tests/test_api_habit_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py -q`

Run: `cd web && pnpm test -- src/actions/habits.test.ts src/components/personal-actions/habit-controls.test.tsx src/lib/personal-workspace.test.ts src/lib/dashboard.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Commit habit lifecycle**

```bash
git add modules/habits.py tests/test_habits.py api/habit_mutations.py api/main.py api/personal.py api/dashboard.py api/models.py api/workspace_models.py tests/test_api_habit_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py web/src/actions/habits.ts web/src/actions/habits.test.ts web/src/lib web/src/components/personal-actions/habit-controls.tsx web/src/components/personal-actions/habit-controls.test.tsx web/src/components/habits-workspace.tsx web/src/components/personal-workspace.module.css web/src/app/habitos/page.tsx
git commit -m "feat: migrar ciclo de habitos com leitura pura"
```

---

### Task 5: Add reading lifecycle mutations

**Files:**
- Modify: `modules/reading.py`
- Create: `tests/test_reading.py`
- Create: `api/reading_mutations.py`
- Create: `tests/test_api_reading_mutations.py`
- Modify: `api/main.py`
- Modify: `api/personal.py`
- Modify: `api/dashboard.py`
- Modify: `api/models.py`
- Modify: `tests/test_api_dashboard.py`
- Modify: `tests/test_api_workspaces.py`
- Create: `web/src/actions/reading.ts`
- Create: `web/src/actions/reading.test.ts`
- Modify: `web/src/lib/personal-mutation-contracts.ts`
- Modify: `web/src/lib/personal-workspace.ts`
- Modify: `web/src/lib/dashboard.ts`
- Create: `web/src/components/personal-actions/reading-controls.tsx`
- Create: `web/src/components/personal-actions/reading-controls.test.tsx`
- Modify: `web/src/components/reading-workspace.tsx`
- Modify: `web/src/components/personal-workspace.module.css`
- Modify: `web/src/app/leitura/page.tsx`

**Interfaces:**
- Produces: `ReadingIdConflict`.
- Produces: `reading.add(title, author, total_pages, daily_goal, item_id=None) -> tuple[dict, bool]`.
- Produces: `reading.set_progress(book_id, *, current_page=None, status=None) -> tuple[dict | None, bool]`.
- Produces: `POST /v1/books`, `PATCH /v1/books/{id}`, `DELETE /v1/books/{id}`.
- Extends: Today `Reading` with persistent `id` and `mutable`.

- [ ] **Step 1: Write failing domain and API tests**

```python
def test_progress_reaching_last_page_marks_book_complete(monkeypatch):
    stored = {"id": "book-1", "pagina_atual": "20", "total_paginas": "100", "status": "Lendo"}
    monkeypatch.setattr(reading, "records", lambda _name: [stored])
    updates = []
    monkeypatch.setattr(reading, "update_record", lambda _name, _id, values: updates.append(values) or True)
    record, changed = reading.set_progress("book-1", current_page=100)
    assert changed is True
    assert record["pagina_atual"] == 100
    assert record["status"] == "Concluído"
    assert updates == [{"pagina_atual": 100, "status": "Concluído"}]


@pytest.mark.parametrize("page", [-1, 101])
def test_progress_rejects_page_outside_book(page):
    with pytest.raises(ValueError):
        reading.set_progress("book-1", current_page=page)
```

Cover RAW create and stable replay, ID conflict, empty title, positive total/goal, safe legacy numeric parsing, reopen preserving page, explicit complete setting page to total, no-op replay, repeated delete, API guards, lock, cache and safe audit.

- [ ] **Step 2: Run reading tests and confirm RED**

Run: `python -m pytest tests/test_reading.py tests/test_api_reading_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py -q`

Expected: FAIL for missing idempotent lifecycle functions and routes.

- [ ] **Step 3: Implement domain and API contracts**

`PATCH /v1/books/{id}` accepts optional `currentPage` and `status`, rejects an empty patch, restricts status to `Lendo` or `Concluído`, and validates against the confirmed total. `status: "Concluído"` sets the page to total; `status: "Lendo"` preserves the current page. Creates write all text with `RAW` and return `{ operationId, created, book }`.

- [ ] **Step 4: Write failing web action and DOM tests**

Test stable create ID, field errors, page bounds, completion, reopen, delete confirmation, response mismatch, closed gates, exact revalidation, pending buttons and failed-form preservation.

```tsx
it("preserva a página digitada quando a API falha", async () => {
  render(<ReadingControls book={book} canMutate />);
  const page = screen.getByLabelText("Página atual");
  await userEvent.clear(page);
  await userEvent.type(page, "64");
  await userEvent.click(screen.getByRole("button", { name: "Salvar leitura" }));
  expect(page).toHaveValue(64);
  expect(await screen.findByText("Não foi possível atualizar a leitura agora.")).toBeInTheDocument();
});
```

- [ ] **Step 5: Implement Server Actions, forms and workspace controls**

Create `createBookAction`, `updateBookAction` and `deleteBookAction`. Use numeric HTML bounds as convenience only; Zod and FastAPI remain authoritative. The server page supplies a stable create UUID. Completed books expose `Voltar a ler`; active books expose `Concluir`. Legacy books without IDs remain visible with disabled controls.

- [ ] **Step 6: Run focused verification**

Run: `python -m pytest tests/test_reading.py tests/test_api_reading_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py -q`

Run: `cd web && pnpm test -- src/actions/reading.test.ts src/components/personal-actions/reading-controls.test.tsx src/lib/personal-workspace.test.ts src/lib/dashboard.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Commit reading lifecycle**

```bash
git add modules/reading.py tests/test_reading.py api/reading_mutations.py api/main.py api/personal.py api/dashboard.py api/models.py tests/test_api_reading_mutations.py tests/test_api_dashboard.py tests/test_api_workspaces.py web/src/actions/reading.ts web/src/actions/reading.test.ts web/src/lib web/src/components/personal-actions/reading-controls.tsx web/src/components/personal-actions/reading-controls.test.tsx web/src/components/reading-workspace.tsx web/src/components/personal-workspace.module.css web/src/app/leitura/page.tsx
git commit -m "feat: migrar acompanhamento de leitura"
```

---

### Task 6: Add idempotent physical activity registration

**Files:**
- Modify: `modules/activity.py`
- Create: `tests/test_activity.py`
- Create: `api/activity_mutations.py`
- Create: `tests/test_api_activity_mutations.py`
- Modify: `api/main.py`
- Modify: `api/personal.py`
- Modify: `tests/test_api_workspaces.py`
- Create: `web/src/actions/activity.ts`
- Create: `web/src/actions/activity.test.ts`
- Modify: `web/src/lib/personal-mutation-contracts.ts`
- Modify: `web/src/lib/personal-workspace.ts`
- Create: `web/src/components/personal-actions/activity-controls.tsx`
- Create: `web/src/components/personal-actions/activity-controls.test.tsx`
- Modify: `web/src/components/activity-workspace.tsx`
- Modify: `web/src/components/personal-workspace.module.css`
- Modify: `web/src/app/atividade/page.tsx`

**Interfaces:**
- Produces: `ActivityIdConflict`.
- Produces: `activity.add(activity_type, target_date=None, item_id=None) -> tuple[dict, bool, bool]`, where booleans mean `created` and `changed`.
- Produces: `POST /v1/activities` with `{ id, date, type }`.
- Preserves: XP key `activity:<date>:<normalized-type>`.

- [ ] **Step 1: Write failing domain and API tests**

```python
def test_same_type_and_date_is_semantic_replay(monkeypatch):
    existing = {"id": "old-id", "data": "2026-08-25", "tipo": "Corrida", "feito": "Sim"}
    monkeypatch.setattr(activity, "records", lambda _name: [existing])
    monkeypatch.setattr(activity, "append_record", lambda *_args, **_kwargs: pytest.fail("must not append"))
    monkeypatch.setattr(activity, "award_xp_once", lambda *_args: pytest.fail("must not award again"))
    record, created, changed = activity.add("  Corrida  ", date(2026, 8, 25), item_id="new-id")
    assert record == existing
    assert (created, changed) == (False, False)


def test_legacy_pending_record_is_completed_without_duplicate_row(monkeypatch):
    # same date and normalized type, feito != Sim
    record, created, changed = activity.add("Treino", date(2026, 8, 25), item_id="new-id")
    assert (created, changed) == (False, True)
    assert updates == [("Atividade", "legacy-id", {"feito": "Sim"})]
```

Also test stable ID conflict, RAW create, allowed types plus trimmed `Outro`, ISO date, API guard order, semantic replay response, lock, cache and XP event key.

- [ ] **Step 2: Run activity tests and confirm RED**

Run: `python -m pytest tests/test_activity.py tests/test_api_activity_mutations.py tests/test_api_workspaces.py -q`

Expected: FAIL because the current function is tied to today and returns no confirmation.

- [ ] **Step 3: Implement activity domain and API router**

Normalize type with trimmed text and casefold only for comparison; preserve the user's canonical trimmed spelling in storage. If the semantic record exists, return its ID even when it differs from the requested create UUID. Award XP only through `award_xp_once`; a semantic replay may call it only when completing a previously pending record.

- [ ] **Step 4: Write failing Server Action and component tests**

Test stable create UUID, type/date validation, acceptance of a semantic replay with a different returned ID, response date/type confirmation, closed gates, exact `/atividade` plus `/` revalidation, pending button and retry value preservation.

- [ ] **Step 5: Implement activity action and form**

Create `registerActivityAction`. Offer the current five types (`Treino`, `Caminhada`, `Corrida`, `Alongamento`, `Outro`) and a selected date. The page supplies one stable UUID, the form rotates it only after a confirmed response, and existing daily records remain readable defensively.

- [ ] **Step 6: Run focused verification**

Run: `python -m pytest tests/test_activity.py tests/test_api_activity_mutations.py tests/test_api_workspaces.py -q`

Run: `cd web && pnpm test -- src/actions/activity.test.ts src/components/personal-actions/activity-controls.test.tsx src/lib/personal-workspace.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Commit activity registration**

```bash
git add modules/activity.py tests/test_activity.py api/activity_mutations.py api/main.py api/personal.py tests/test_api_activity_mutations.py tests/test_api_workspaces.py web/src/actions/activity.ts web/src/actions/activity.test.ts web/src/lib web/src/components/personal-actions/activity-controls.tsx web/src/components/personal-actions/activity-controls.test.tsx web/src/components/activity-workspace.tsx web/src/components/personal-workspace.module.css web/src/app/atividade/page.tsx
git commit -m "feat: migrar registro de atividade fisica"
```

---

### Task 7: Reuse personal actions on Today

**Files:**
- Modify: `api/models.py`
- Modify: `api/dashboard.py`
- Modify: `tests/test_api_dashboard.py`
- Modify: `web/src/lib/dashboard.ts`
- Modify: `web/src/lib/dashboard.test.ts`
- Modify: `web/src/lib/demo-dashboard.ts`
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/today-dashboard.tsx`
- Modify: `web/src/components/today-dashboard.module.css`
- Create: `web/src/components/today-actions.test.tsx`
- Modify: `web/src/components/personal-actions/task-controls.tsx`
- Modify: `web/src/components/personal-actions/routine-controls.tsx`
- Modify: `web/src/components/personal-actions/habit-controls.tsx`
- Modify: `web/src/components/personal-actions/reading-controls.tsx`
- Modify: `web/src/components/personal-actions/activity-controls.tsx`

**Interfaces:**
- Produces: Today-specific `TodayTask`, `AgendaItem`, `Reading` and `Habit` models with persistent identity and `mutable` metadata; shared read-only models outside Today keep their existing contracts.
- Adds: `AgendaItem.kind: "fixed" | "custom"` and `sourceId`.
- Adds: `Habit.configId`, nullable `logId`, and `streakDays`.
- Adds: `Reading.id` and `mutable`.
- Reuses: all Server Actions from Tasks 2 through 6; creates no Today-specific write endpoint.

- [ ] **Step 1: Write failing API and TypeScript contract tests for actionable identity**

```python
def test_today_marks_only_persistent_personal_rows_mutable():
    dashboard = build_today_dashboard(tables, date(2026, 8, 25))
    assert dashboard.priorities[0].mutable is True
    assert dashboard.priorities[1].mutable is False
    assert next(item for item in dashboard.agenda if item.kind == "fixed").mutable is False
    assert next(item for item in dashboard.agenda if item.kind == "custom").mutable is True
    assert dashboard.habits[0].config_id == "habit-config-1"
    assert dashboard.habits[0].log_id is None
```

Update the TypeScript guards so an API response missing the new identity fields is rejected instead of silently enabling the wrong control.

- [ ] **Step 2: Run contract tests and confirm RED**

Run: `python -m pytest tests/test_api_dashboard.py -q`

Run: `cd web && pnpm test -- src/lib/dashboard.test.ts`

Expected: FAIL because Today does not yet expose sufficient source identity.

- [ ] **Step 3: Implement Today read-model identity without writing**

Use the original row ID only when non-empty. Keep a synthetic display ID for React keys but set `mutable: false`. For agenda, expose raw `sourceId` separately from the display ID and mark every weekly item read-only. Include the active reading ID and habit config/log IDs. Do not call any domain mutation from dashboard construction.

- [ ] **Step 4: Write failing Today component tests**

```tsx
it("reutiliza controles somente nos registros pessoais mutáveis", () => {
  render(<TodayDashboard dashboard={actionableDashboard} source="api" canMutate />);
  expect(screen.getByRole("button", { name: "Concluir tarefa Prioridade real" })).toBeInTheDocument();
  expect(screen.getByText("Agenda fixa")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /concluir.*Aula fixa/i })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Marcar Ler" })).toBeInTheDocument();
});
```

Also test `canMutate: false`, demo source, legacy rows, task quick-create stable UUID, reading update, activity registration, pending/error messages and absence of duplicate form IDs.

- [ ] **Step 5: Implement Today controls by composing existing components**

The Today server page passes `canMutate = source === "api" && mutationsUiEnabled()` and stable UUIDs for quick task and activity creation. Add compact variants to the existing personal control components rather than duplicating their logic. Replace the obsolete footer claiming that no writes are sent with a neutral data-source status; when gates are closed, render one concise unavailable message for the page.

- [ ] **Step 6: Run Today and affected-domain tests**

Run: `python -m pytest tests/test_api_dashboard.py tests/test_api_workspaces.py -q`

Run: `cd web && pnpm test -- src/components/today-actions.test.tsx src/lib/dashboard.test.ts src/actions/tasks.test.ts src/actions/routine.test.ts src/actions/habits.test.ts src/actions/reading.test.ts src/actions/activity.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Commit Today integration**

```bash
git add api/models.py api/dashboard.py tests/test_api_dashboard.py web/src/lib/dashboard.ts web/src/lib/dashboard.test.ts web/src/lib/demo-dashboard.ts web/src/app/page.tsx web/src/components/today-dashboard.tsx web/src/components/today-dashboard.module.css web/src/components/today-actions.test.tsx web/src/components/personal-actions
git commit -m "feat: adicionar acoes pessoais ao painel hoje"
```

---

### Task 8: Update operational documentation and Server Action artifact coverage

**Files:**
- Modify: `api/README.md`
- Modify: `web/README.md`
- Modify: `web/tests/server-action-build.check.mjs`
- Modify: `docs/superpowers/specs/2026-08-25-nexo-personal-routine-design.md` only if implementation forced an explicitly approved design clarification
- Create during execution: `.superpowers/sdd/2026-08-25-nexo-personal-routine/task-*-report.md`

**Interfaces:**
- Documents: all new mutation routes, their closed-by-default gates and one-process lock limitation.
- Verifies: every public Server Action artifact contains only intended async exports and no private configuration marker.
- Preserves: no deploy, real OAuth, real Sheets write, backfill apply or gate activation.

- [ ] **Step 1: Extend the failing build-artifact test before documentation changes**

```js
const expectedActions = {
  "src/actions/tasks.ts": ["createTaskAction", "deleteTaskAction", "setTaskCompletedAction"],
  "src/actions/routine.ts": ["createRoutineItemAction", "deleteRoutineItemAction", "setRoutineItemCompletedAction"],
  "src/actions/habits.ts": ["createHabitAction", "setHabitActiveAction", "setHabitCompletedAction"],
  "src/actions/reading.ts": ["createBookAction", "deleteBookAction", "updateBookAction"],
  "src/actions/activity.ts": ["registerActivityAction"],
};
```

Scan every server reference manifest and compare the set of exported action names per file. Continue scanning `.next/static` for `NEXO_API_TOKEN`, `NEXO_API_URL`, service-account markers and the actual test token.

- [ ] **Step 2: Run the artifact check and confirm RED if new modules are not covered**

Run: `cd web && pnpm build`

Expected before the test update is complete: FAIL because the manifest assertions do not cover all action modules. Expected after implementing the exact export map: PASS.

- [ ] **Step 3: Update API and web runbooks**

Document these mutation groups without real values:

```text
POST/PATCH/DELETE /v1/tasks
POST/PATCH/DELETE /v1/routine-items
POST/PATCH /v1/habits
PUT /v1/habit-checkins/{config_id}/{date}
POST/PATCH/DELETE /v1/books
POST /v1/activities
```

State explicitly that both write gates remain false, Streamlit remains the writer, the API remains limited to one process, the backfill is not executed, and Delivery 3 owns weekly agenda check-ins.

- [ ] **Step 4: Run documentation and artifact checks**

Run: `git diff --check`

Run: `cd web && pnpm build`

Expected: no whitespace errors; build and both artifact tests PASS.

- [ ] **Step 5: Commit runbook and artifact coverage**

```bash
git add api/README.md web/README.md web/tests/server-action-build.check.mjs .superpowers/sdd/2026-08-25-nexo-personal-routine
git commit -m "docs: registrar operacao segura da rotina pessoal"
```

---

### Task 9: Run full verification and two-stage review

**Files:**
- Review: every file changed since `b4bf9d3c3b55eca6d698f92aef28d02a32179f9b`
- Create: `.superpowers/sdd/2026-08-25-nexo-personal-routine/final-verification.md`
- Create if fixes are needed: `.superpowers/sdd/2026-08-25-nexo-personal-routine/final-fix-report.md`

**Interfaces:**
- Consumes: all previous task deliverables.
- Produces: a clean branch ready for a Pull Request, with evidence and no production activation.

- [ ] **Step 1: Run the complete Python suite and import checks**

Run: `python -m pytest -q`

Run: `python -m compileall -q api modules views app.py`

Run: `python -c "from api.main import app; from modules import activity, habits, reading, routine, tasks; print(len(app.routes))"`

Expected: all tests PASS; compile and imports exit 0.

- [ ] **Step 2: Run the complete web verification**

Run: `cd web && pnpm test`

Run: `cd web && pnpm lint`

Run: `cd web && pnpm typecheck`

Run: `cd web && pnpm build`

Expected: all tests, lint, typecheck, production build and artifact checks PASS.

- [ ] **Step 3: Run repository safety checks**

Run: `git diff --check b4bf9d3c3b55eca6d698f92aef28d02a32179f9b..HEAD`

Run: `git diff --name-only b4bf9d3c3b55eca6d698f92aef28d02a32179f9b..HEAD`

Run: `git grep -n -E "BEGIN PRIVATE KEY|NEXO_API_TOKEN=.+|GSHEETS_SERVICE_ACCOUNT_JSON=.+" -- ':!*.example' ':!docs/superpowers/plans/*'`

Run: `git grep -n "NEXO_.*WRITES_ENABLED=true" -- ':!tests/**' ':!web/src/**/*.test.*' ':!docs/superpowers/plans/*'`

Expected: clean diff; no committed secret values; no production configuration enabling either gate.

- [ ] **Step 4: Review each task against the spec, then review overall code quality**

The first review checks exact spec compliance, route guards, desired-state behavior, legacy rows, XP event keys, cache invalidation, Today reuse and excluded weekly check-ins. The second review checks maintainability, duplication, unsafe conversions, ambiguous responses, accessibility and private-data leakage. Record findings with file and line evidence.

- [ ] **Step 5: Fix every accepted finding with a focused failing test**

For each defect, add the smallest regression test that fails for the observed behavior, run it to confirm RED, implement the correction, rerun the focused test to GREEN, then repeat Steps 1 through 3 in full. Do not alter the approved scope while fixing review findings.

- [ ] **Step 6: Record final evidence and commit review fixes**

```bash
git add api modules tests views web .superpowers/sdd/2026-08-25-nexo-personal-routine
git commit -m "test: concluir verificacao da rotina pessoal"
```

If there are no file changes after verification, do not create an empty commit. Record exact command output summaries, test counts, reviewed commit range and any accepted residual limitation in `final-verification.md`.

- [ ] **Step 7: Prepare the Pull Request without activating production**

Push `agent/nexo-personal-routine`, open a PR to `main`, wait for required checks, and report the PR URL. Do not mark it merged until checks and review are green. Merging this delivery still leaves both production write gates disabled and does not execute any backfill or deploy command.
