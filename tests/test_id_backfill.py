import json
from pathlib import Path
import subprocess
import sys

import pytest

from modules import id_backfill
from modules.id_backfill import collect_missing_id_updates
from scripts import backfill_missing_ids as backfill_cli


FIRST_UUID = "0f3ac9b0-5779-40ce-834d-40a8657684af"
SECOND_UUID = "b6f79644-8787-40a7-8d5d-4f83078657ab"


def reviewed_plan(*worksheets):
    return {
        "schema": "nexo-id-backfill-plan",
        "version": 1,
        "worksheets": list(worksheets),
    }


def present_sheet(name, updates=()):
    return {
        "worksheet": name,
        "state": "present",
        "expected_header": list(id_backfill.SHEETS[name]),
        "updates": list(updates),
    }


def missing_sheet(name):
    return {
        "worksheet": name,
        "state": "missing",
        "expected_header": list(id_backfill.SHEETS[name]),
        "updates": [],
    }


def planned_update(row, value):
    return {"cell": f"A{row}", "row": row, "uuid": value}


def test_backfill_only_targets_empty_id_cells():
    """Changing the row enumeration must not move legacy IDs to wrong cells."""
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


def test_backfill_skips_empty_legacy_rows():
    rows = [
        ["id", "data", "tarefa", "categoria", "status"],
        ["", "", "", "", ""],
    ]

    assert collect_missing_id_updates("Tarefas", rows, id_factory=lambda: "unused") == []


def test_backfill_refuses_an_unexpected_header():
    with pytest.raises(RuntimeError, match="cabeçalho esperado"):
        collect_missing_id_updates(
            "Tarefas",
            [["id", "tarefa"], ["", "Revisar"]],
        )


def test_plan_distinguishes_missing_sheet_from_present_sheet_without_pending_ids(
    monkeypatch,
):
    """Collapsing worksheet states into counts must make this test fail."""

    class Worksheet:
        def get(self, **kwargs):
            assert kwargs == {"pad_values": True}
            return [list(id_backfill.SHEETS["Tarefas"])]

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas", "Rotina"))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda name: Worksheet() if name == "Tarefas" else None,
    )

    plan = id_backfill.build_backfill_plan()

    assert plan == reviewed_plan(
        present_sheet("Tarefas"),
        missing_sheet("Rotina"),
    )


def test_plan_persists_exact_row_cell_and_uuid_without_row_content(monkeypatch):
    """Replacing reviewed UUIDs during apply must make this test fail."""
    rows = [
        list(id_backfill.SHEETS["Tarefas"]),
        ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
    ]

    class Worksheet:
        def get(self, **_kwargs):
            return rows

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda _name: Worksheet(),
    )

    plan = id_backfill.build_backfill_plan(id_factory=lambda: FIRST_UUID)

    assert plan == reviewed_plan(
        present_sheet("Tarefas", [planned_update(2, FIRST_UUID)]),
    )
    serialized = json.dumps(plan, ensure_ascii=False)
    assert "Revisar" not in serialized
    assert "Estudo" not in serialized


def test_apply_revalidates_every_sheet_then_writes_exact_reviewed_plan_once(
    monkeypatch,
):
    """Replanning UUIDs or writing before global validation must fail this test."""
    rows = {
        "Tarefas": [
            list(id_backfill.SHEETS["Tarefas"]),
            ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
        ],
        "Rotina": [
            list(id_backfill.SHEETS["Rotina"]),
            ["", "2026-08-23", "08:00", "Treinar", "Pendente"],
        ],
    }
    reads = []
    writes = []

    class Worksheet:
        def __init__(self, name):
            self.name = name

        def get(self, **kwargs):
            assert kwargs == {"pad_values": True}
            reads.append(self.name)
            return rows[self.name]

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas", "Rotina"))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda name: Worksheet(name),
    )
    monkeypatch.setattr(
        id_backfill,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )
    plan = reviewed_plan(
        present_sheet("Tarefas", [planned_update(2, FIRST_UUID)]),
        present_sheet("Rotina", [planned_update(2, SECOND_UUID)]),
    )

    counts = id_backfill.apply_backfill_plan(plan)

    assert reads == ["Tarefas", "Rotina"]
    assert counts == {"Tarefas": 1, "Rotina": 1}
    assert writes == [[
        {"sheet": "Tarefas", "range": "A2", "values": [[FIRST_UUID]]},
        {"sheet": "Rotina", "range": "A2", "values": [[SECOND_UUID]]},
    ]]


@pytest.mark.parametrize("stale_kind", ["filled_target", "changed_header"])
def test_apply_aborts_with_zero_writes_when_any_precondition_is_stale(
    monkeypatch,
    stale_kind,
):
    """A partial batch after one stale precondition must make this test fail."""
    task_rows = [
        list(id_backfill.SHEETS["Tarefas"]),
        ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
    ]
    routine_header = list(id_backfill.SHEETS["Rotina"])
    if stale_kind == "changed_header":
        routine_header[-1] = "estado_inesperado"
    routine_id = SECOND_UUID if stale_kind == "filled_target" else ""
    routine_rows = [
        routine_header,
        [routine_id, "2026-08-23", "08:00", "Treinar", "Pendente"],
    ]
    rows = {"Tarefas": task_rows, "Rotina": routine_rows}
    writes = []

    class Worksheet:
        def __init__(self, name):
            self.name = name

        def get(self, **_kwargs):
            return rows[self.name]

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas", "Rotina"))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda name: Worksheet(name),
    )
    monkeypatch.setattr(
        id_backfill,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )
    plan = reviewed_plan(
        present_sheet("Tarefas", [planned_update(2, FIRST_UUID)]),
        present_sheet("Rotina", [planned_update(2, SECOND_UUID)]),
    )

    with pytest.raises(RuntimeError, match="plano ficou desatualizado"):
        id_backfill.apply_backfill_plan(plan)

    assert writes == []


def test_apply_revalidates_a_missing_worksheet_state(monkeypatch):
    """Treating a newly-created sheet as still missing must fail this test."""

    class Worksheet:
        def get(self, **_kwargs):
            return [list(id_backfill.SHEETS["Tarefas"])]

    writes = []
    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda _name: Worksheet(),
    )
    monkeypatch.setattr(
        id_backfill,
        "write_values_batch",
        lambda updates: writes.append(updates),
    )

    with pytest.raises(RuntimeError, match="plano ficou desatualizado"):
        id_backfill.apply_backfill_plan(reviewed_plan(missing_sheet("Tarefas")))

    assert writes == []


def test_plan_schema_rejects_non_uuid_and_unreviewed_fields(monkeypatch):
    """A plan carrying arbitrary payload or a non-UUID must never reach writes."""
    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    plan = reviewed_plan(
        {
            **present_sheet("Tarefas", [planned_update(2, "not-a-uuid")]),
            "payload": "texto privado",
        },
    )

    with pytest.raises(ValueError, match="plano inválido"):
        id_backfill.validate_backfill_plan(plan)


def test_cli_dry_run_prints_complete_plan_and_persists_review_file(
    monkeypatch,
    tmp_path,
    capsys,
):
    """Printing only counts must make this real CLI-path test fail."""
    plan = reviewed_plan(
        present_sheet("Tarefas", [planned_update(2, FIRST_UUID)]),
        present_sheet("Rotina"),
        missing_sheet("Erros"),
    )
    plan_path = tmp_path / "reviewed-backfill-plan.json"
    monkeypatch.setattr(backfill_cli, "build_backfill_plan", lambda: plan)

    assert backfill_cli.main(["--plan-out", str(plan_path)]) == 0

    output = capsys.readouterr().out
    assert "Tarefas: presente, 1 ID(s) pendente(s)" in output
    assert f"linha 2 | célula A2 | UUID {FIRST_UUID}" in output
    assert "Rotina: presente, sem IDs pendentes" in output
    assert "Erros: ausente" in output
    assert str(plan_path) in output
    assert json.loads(plan_path.read_text(encoding="utf-8")) == plan


@pytest.mark.parametrize("confirmation", [None, "backfill_ids", " BACKFILL_IDS "])
def test_cli_apply_requires_literal_confirmation_and_explicit_plan_file(
    monkeypatch,
    tmp_path,
    confirmation,
):
    """An apply without the exact reviewed-file ceremony must fail."""
    plan_path = tmp_path / "reviewed-plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        backfill_cli,
        "apply_backfill_plan",
        lambda _plan: pytest.fail("apply must not run"),
    )
    argv = ["--apply-plan", str(plan_path)]
    if confirmation is not None:
        argv.extend(["--confirm", confirmation])

    with pytest.raises(SystemExit) as error:
        backfill_cli.main(argv)

    assert error.value.code == 2


def test_cli_apply_consumes_reviewed_file_without_replanning(
    monkeypatch,
    tmp_path,
    capsys,
):
    """Calling the live planner during apply must make this test fail."""
    plan = reviewed_plan(
        present_sheet("Tarefas", [planned_update(2, FIRST_UUID)]),
    )
    plan_path = tmp_path / "reviewed-plan.json"
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False),
        encoding="utf-8",
    )
    applied = []
    monkeypatch.setattr(
        backfill_cli,
        "build_backfill_plan",
        lambda: pytest.fail("apply must not replan"),
    )
    monkeypatch.setattr(
        backfill_cli,
        "apply_backfill_plan",
        lambda loaded: applied.append(loaded) or {"Tarefas": 1},
    )

    assert backfill_cli.main([
        "--apply-plan",
        str(plan_path),
        "--confirm",
        "BACKFILL_IDS",
    ]) == 0

    assert applied == [plan]
    assert "Tarefas: 1 ID(s) aplicado(s)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "command",
    [
        (sys.executable, "scripts/backfill_missing_ids.py", "--help"),
        (sys.executable, "-m", "scripts.backfill_missing_ids", "--help"),
    ],
)
def test_backfill_cli_help_runs_from_project_root(command):
    result = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "--apply-plan" in result.stdout
    assert "--plan-out" in result.stdout
