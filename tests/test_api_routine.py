import copy
from datetime import date

import pytest

from api.routine import build_routine_dashboard
from api.sheets import DASHBOARD_SHEETS


def empty_tables():
    return {name: [] for name in DASHBOARD_SHEETS}


def test_routine_combines_fixed_and_custom_items_without_mutating_tables():
    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "3420"}],
            "AgendaSemanal": [
                {
                    "id": "a1",
                    "dia_semana": "Sábado",
                    "hora": "9:00",
                    "atividade": "Curso",
                    "categoria": "Estudo",
                    "ativo": "Sim",
                },
                {
                    "id": "a2",
                    "dia_semana": "Sábado",
                    "hora": "07:00",
                    "atividade": "Arquivado",
                    "ativo": "Não",
                },
            ],
            "AgendaCheckins": [
                {
                    "data": "2026-08-22",
                    "agenda_id": "a1",
                    "status": "Concluída",
                }
            ],
            "Rotina": [
                {
                    "id": "r1",
                    "data": "2026-08-22",
                    "hora": "08:30",
                    "atividade": "Mercado",
                    "status": "Pendente",
                },
                {
                    "id": "r2",
                    "data": "2026-08-23",
                    "hora": "10:00",
                    "atividade": "Outro dia",
                    "status": "Pendente",
                },
            ],
        }
    )
    original = copy.deepcopy(tables)

    payload = build_routine_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert tables == original
    assert payload["date"] == "2026-08-22"
    assert payload["total"] == 2
    assert payload["completed"] == 1
    assert payload["fixedCount"] == 1
    assert payload["customCount"] == 1
    assert [item["title"] for item in payload["items"]] == ["Mercado", "Curso"]
    assert payload["items"][0]["id"] == "custom:r1"
    assert payload["items"][0]["sourceId"] == "r1"
    assert payload["items"][0]["mutable"] is True
    assert payload["items"][1]["sourceId"] == ""
    assert payload["items"][1]["mutable"] is False
    assert payload["items"][1]["completed"] is True


def test_routine_tolerates_incomplete_legacy_rows():
    tables = empty_tables()
    tables.update(
        {
            "AgendaSemanal": [
                {
                    "dia_semana": "Sábado",
                    "hora": "sem-hora",
                    "ativo": "Sim",
                }
            ],
            "Rotina": [
                {
                    "data": "2026-08-22",
                    "hora": "99:99",
                }
            ],
        }
    )

    payload = build_routine_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["total"] == 2
    assert payload["completed"] == 0
    assert payload["items"][0]["title"] == "Compromisso sem título"
    assert payload["items"][0]["sourceId"] == ""
    assert payload["items"][0]["mutable"] is False
    assert payload["items"][1]["title"] == "Atividade sem título"
    assert payload["items"][1]["sourceId"] == ""
    assert payload["items"][1]["mutable"] is False


def test_fixed_items_ignore_persistent_identity_for_mutation_controls():
    tables = empty_tables()
    tables["AgendaSemanal"] = [
        {
            "id": "weekly-1",
            "dia_semana": "Sábado",
            "hora": "08:00",
            "atividade": "Curso",
            "ativo": "Sim",
        }
    ]

    payload = build_routine_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["items"][0]["kind"] == "fixed"
    assert payload["items"][0]["sourceId"] == ""
    assert payload["items"][0]["mutable"] is False


@pytest.mark.parametrize(
    ("id_length", "expected_mutable"),
    [(512, True), (513, False)],
)
def test_custom_items_respect_the_safe_identity_limit(
    id_length,
    expected_mutable,
):
    tables = empty_tables()
    item_id = "i" * id_length
    tables["Rotina"] = [
        {
            "id": item_id,
            "data": "2026-08-22",
            "hora": "08:30",
            "atividade": "Legado",
            "status": "Pendente",
        }
    ]

    payload = build_routine_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["items"][0]["sourceId"] == item_id
    assert payload["items"][0]["mutable"] is expected_mutable


@pytest.mark.parametrize(
    ("item_id", "expected_mutable"),
    [
        (".", False),
        ("..", False),
        ("legacy..item", True),
        ("legacy/folder.item", True),
    ],
)
def test_custom_items_reject_only_unsafe_dot_segment_identities(
    item_id,
    expected_mutable,
):
    tables = empty_tables()
    tables["Rotina"] = [
        {
            "id": item_id,
            "data": "2026-08-22",
            "hora": "08:30",
            "atividade": "Legado",
            "status": "Pendente",
        }
    ]

    payload = build_routine_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["items"][0]["sourceId"] == item_id
    assert payload["items"][0]["mutable"] is expected_mutable
