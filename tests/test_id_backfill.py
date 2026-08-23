from pathlib import Path
import subprocess
import sys

import pytest

from modules import id_backfill
from modules.id_backfill import collect_missing_id_updates
from scripts.backfill_missing_ids import should_apply


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


def test_backfill_defaults_to_dry_run(monkeypatch):
    rows = [
        ["id", "data", "tarefa", "categoria", "status"],
        ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
    ]
    writes = []

    class Worksheet:
        def get(self, **kwargs):
            assert kwargs == {"pad_values": True}
            return rows

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda _name: Worksheet(),
        raising=False,
    )
    monkeypatch.setattr(id_backfill, "write_values_batch", lambda updates: writes.append(updates))

    assert id_backfill.backfill_missing_ids() == {"Tarefas": 1}
    assert writes == []


def test_dry_run_does_not_create_a_missing_worksheet(monkeypatch):
    creation_attempts = []
    writes = []

    def create_missing_worksheet(_name):
        creation_attempts.append(_name)
        raise AssertionError("dry-run must not create a worksheet")

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    monkeypatch.setattr(
        id_backfill,
        "get_worksheet",
        create_missing_worksheet,
        raising=False,
    )
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda _name: None,
        raising=False,
    )
    monkeypatch.setattr(id_backfill, "write_values_batch", lambda updates: writes.append(updates))

    assert id_backfill.backfill_missing_ids() == {"Tarefas": 0}
    assert creation_attempts == []
    assert writes == []


def test_backfill_applies_all_missing_ids_in_one_batch(monkeypatch):
    rows = [
        ["id", "data", "tarefa", "categoria", "status"],
        ["", "2026-08-22", "Revisar", "Estudo", "Pendente"],
        ["", "2026-08-23", "Treinar", "Saúde", "Concluída"],
    ]
    writes = []

    class Worksheet:
        def get(self, **_kwargs):
            return rows

    monkeypatch.setattr(id_backfill, "ID_SHEETS", ("Tarefas",))
    monkeypatch.setattr(
        id_backfill,
        "get_existing_worksheet",
        lambda _name: Worksheet(),
        raising=False,
    )
    monkeypatch.setattr(id_backfill, "write_values_batch", lambda updates: writes.append(updates))
    monkeypatch.setattr(id_backfill.uuid, "uuid4", lambda: "stable-id")

    assert id_backfill.backfill_missing_ids(apply=True) == {"Tarefas": 2}
    assert writes == [
        [
            {"sheet": "Tarefas", "range": "A2", "values": [["stable-id"]]},
            {"sheet": "Tarefas", "range": "A3", "values": [["stable-id"]]},
        ]
    ]


def test_backfill_cli_requires_exact_confirmation():
    assert should_apply(True, "BACKFILL_IDS") is True
    assert should_apply(True, "backfill_ids") is False
    assert should_apply(False, "BACKFILL_IDS") is False


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
    assert "--apply" in result.stdout
