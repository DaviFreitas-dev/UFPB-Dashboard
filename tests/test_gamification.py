from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date

import pytest

from modules import gamification


def _apply_xp_batch(tables, updates):
    for update in updates:
        sheet = update["sheet"]
        values = update["values"]
        if sheet == "XPEventos":
            row = values[0]
            tables[sheet].append(
                {
                    "id": row[0],
                    "event_key": row[1],
                    "data": row[2],
                    "fonte": row[3],
                    "descricao": row[4],
                    "xp": row[5],
                }
            )
        elif sheet == "Usuario":
            xp_row = next(
                (
                    row
                    for row in tables[sheet]
                    if row.get("chave") == "xp"
                ),
                None,
            )
            if xp_row is None:
                tables[sheet].append({"chave": "xp", "valor": values[0][1]})
            else:
                xp_row["valor"] = values[0][0]
        elif sheet == "Historico":
            row = values[0]
            existing = next(
                (
                    item
                    for item in tables[sheet]
                    if item.get("data") == row[0]
                ),
                None,
            )
            if existing is None:
                tables[sheet].append(
                    {"data": row[0], "horas": row[1], "xp": row[2]}
                )
            else:
                existing.update({"horas": row[1], "xp": row[2]})


def test_award_xp_once_batches_event_balance_and_history(monkeypatch):
    today = str(date.today())
    tables = {
        "XPEventos": [],
        "Usuario": [{"chave": "xp", "valor": "100"}],
        "Historico": [{"data": today, "horas": "2", "xp": "200"}],
    }
    writes = []

    monkeypatch.setattr(
        gamification,
        "records",
        lambda name: deepcopy(tables[name]),
    )
    monkeypatch.setattr(gamification, "new_id", lambda: "event-1")

    def write_values_batch(updates):
        writes.append(deepcopy(updates))
        _apply_xp_batch(tables, updates)

    monkeypatch.setattr(gamification, "write_values_batch", write_values_batch)

    first = gamification.award_xp_once(
        "task:abc",
        15,
        "tarefa",
        "Tarefa concluída",
    )
    second = gamification.award_xp_once(
        "task:abc",
        15,
        "tarefa",
        "Tarefa concluída",
    )

    assert first == 15
    assert second == 0
    assert len(writes) == 1
    ranges = {
        (update["sheet"], update["range"]): update["values"]
        for update in writes[0]
    }
    assert ranges[("XPEventos", "A2:F2")][0][1:] == [
        "task:abc",
        today,
        "tarefa",
        "Tarefa concluída",
        15,
    ]
    assert ranges[("Usuario", "B2")] == [["115"]]
    assert ranges[("Historico", "A2:C2")] == [[today, 2, 215]]


def test_award_xp_once_creates_missing_balance_and_history(monkeypatch):
    writes = []
    tables = {"XPEventos": [], "Usuario": [], "Historico": []}
    monkeypatch.setattr(
        gamification,
        "records",
        lambda name: deepcopy(tables[name]),
    )
    monkeypatch.setattr(gamification, "new_id", lambda: "event-2")
    monkeypatch.setattr(
        gamification,
        "write_values_batch",
        lambda updates: writes.append(deepcopy(updates)),
    )

    awarded = gamification.award_xp_once(
        "habit:abc",
        10,
        "habito",
        "Hábito concluído",
    )

    assert awarded == 10
    ranges = {
        (update["sheet"], update["range"]): update["values"]
        for update in writes[0]
    }
    assert ranges[("Usuario", "A2:B2")] == [["xp", "10"]]
    assert ranges[("Historico", "A2:C2")] == [
        [str(date.today()), 0, 10]
    ]


def test_award_xp_once_does_not_mutate_cache_when_batch_fails(monkeypatch):
    tables = {
        "XPEventos": [],
        "Usuario": [{"chave": "xp", "valor": "100"}],
        "Historico": [],
    }
    monkeypatch.setattr(
        gamification,
        "records",
        lambda name: deepcopy(tables[name]),
    )
    monkeypatch.setattr(gamification, "new_id", lambda: "event-3")
    def fail_write(_updates):
        raise RuntimeError("API indisponível")

    monkeypatch.setattr(gamification, "write_values_batch", fail_write)

    with pytest.raises(RuntimeError, match="API indisponível"):
        gamification.award_xp_once(
            "review:abc",
            20,
            "revisao",
            "Revisão concluída",
        )

    assert tables == {
        "XPEventos": [],
        "Usuario": [{"chave": "xp", "valor": "100"}],
        "Historico": [],
    }


def test_award_xp_once_serializes_concurrent_duplicate_events(monkeypatch):
    tables = {"XPEventos": [], "Usuario": [], "Historico": []}
    writes = []
    monkeypatch.setattr(
        gamification,
        "records",
        lambda name: deepcopy(tables[name]),
    )
    monkeypatch.setattr(gamification, "new_id", lambda: "event-concurrent")

    def write_values_batch(updates):
        writes.append(deepcopy(updates))
        _apply_xp_batch(tables, updates)

    monkeypatch.setattr(gamification, "write_values_batch", write_values_batch)

    def award():
        return gamification.award_xp_once(
            "task:concurrent",
            15,
            "tarefa",
            "Tarefa concluída",
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda _index: award(), range(6)))

    assert sorted(results) == [0, 0, 0, 0, 0, 15]
    assert len(writes) == 1
    assert tables["Usuario"] == [{"chave": "xp", "valor": "15"}]
    assert len(tables["XPEventos"]) == 1


def test_non_positive_award_has_no_side_effects(monkeypatch):
    def fail_read(_name):
        raise AssertionError("unexpected read")

    monkeypatch.setattr(gamification, "records", fail_read)

    assert gamification.award_xp_once("noop", 0, "teste", "Nada") == 0


def test_award_requires_a_non_empty_event_key(monkeypatch):
    def fail_read(_name):
        raise AssertionError("unexpected read")

    monkeypatch.setattr(gamification, "records", fail_read)

    with pytest.raises(ValueError, match="identificador único"):
        gamification.award_xp_once("  ", 10, "teste", "Nada")
