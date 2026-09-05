import copy
from datetime import date

from api.sheets import DASHBOARD_SHEETS


def empty_tables():
    return {name: [] for name in DASHBOARD_SHEETS}


def test_study_workspace_combines_cycle_missions_and_progress_without_writes():
    from api.studies import build_study_workspace

    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "2400"}],
            "Config": [
                {"disciplina": "Matemática", "horas": "5", "ambiente": "Mesa"},
                {"disciplina": "Física", "horas": "3", "ambiente": "Transporte"},
            ],
            "Ciclo": [
                {"disciplina": "Matemática", "restantes": "2"},
                {"disciplina": "Física", "restantes": "3"},
                {"disciplina": "Geografia", "restantes": "1"},
            ],
            "Historico": [
                {"data": "2026-08-20", "horas": "1"},
                {"data": "2026-08-21", "horas": "1.5"},
                {"data": "2026-08-22", "horas": "1"},
                {"data": "2026-08-22", "horas": "0.5"},
            ],
            "Questoes": [
                {"data": "2026-08-12", "feitas": "10", "acertos": "6", "erros": "4"},
                {"data": "2026-08-20", "feitas": "20", "acertos": "15", "erros": "5"},
            ],
            "SessoesEstudo": [
                {
                    "disciplina": "Matemática",
                    "horas": "1.5",
                    "questoes": "10",
                    "acertos": "8",
                    "erros": "2",
                },
                {
                    "disciplina": "Física",
                    "horas": "1",
                    "questoes": "5",
                    "acertos": "3",
                    "erros": "2",
                },
            ],
            "Erros": [
                {
                    "disciplina": "Matemática",
                    "assunto": "Funções",
                    "quantidade": "2",
                    "status": "Aberto",
                },
                {
                    "disciplina": "Matemática",
                    "assunto": "Funções",
                    "quantidade": "3",
                    "status": "Aberto",
                },
            ],
            "Tarefas": [
                {"data": "2026-08-21", "status": "Concluída"},
            ],
            "Revisoes": [
                {"data": "2026-08-20", "status": "Concluída"},
            ],
        }
    )
    original = copy.deepcopy(tables)

    payload = build_study_workspace(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert tables == original
    assert payload["cycle"] == {
        "totalHours": 9.0,
        "remainingHours": 6.0,
        "completedHours": 3.0,
        "progress": 1 / 3,
        "subjects": [
            {
                "id": "cycle-1",
                "subject": "Matemática",
                "environment": "Mesa",
                "plannedHours": 5.0,
                "remainingHours": 2.0,
                "completedHours": 3.0,
                "progress": 0.6,
                "legacy": False,
            },
            {
                "id": "cycle-2",
                "subject": "Física",
                "environment": "Transporte",
                "plannedHours": 3.0,
                "remainingHours": 3.0,
                "completedHours": 0.0,
                "progress": 0.0,
                "legacy": False,
            },
            {
                "id": "cycle-3",
                "subject": "Geografia",
                "environment": "Ambos",
                "plannedHours": 1.0,
                "remainingHours": 1.0,
                "completedHours": 0.0,
                "progress": 0.0,
                "legacy": True,
            },
        ],
    }
    assert payload["missions"]["totalAvailableHours"] == 6.0
    assert payload["missions"]["durationOptions"] == [1, 2, 3, 4, 5, 6]
    assert payload["progress"]["totals"] == {
        "studyHours": 4.0,
        "questions": 30,
        "correct": 21,
        "wrong": 9,
        "accuracy": 0.7,
        "streakDays": 3,
    }
    assert payload["progress"]["studyHistory"][-1] == {
        "date": "2026-08-22",
        "hours": 1.5,
    }
    assert payload["progress"]["weeklyAccuracy"][-1] == {
        "weekStart": "2026-08-17",
        "questions": 20,
        "accuracy": 0.75,
    }
    assert payload["progress"]["reviewPoints"] == [
        {"subject": "Matemática", "topic": "Funções", "quantity": 5}
    ]


def test_study_workspace_tolerates_incomplete_legacy_rows():
    from api.studies import build_study_workspace

    tables = empty_tables()
    tables.update(
        {
            "Config": [
                {
                    "disciplina": "Legada",
                    "horas": "inválido",
                    "ambiente": "Qualquer lugar",
                }
            ],
            "Ciclo": [
                {"disciplina": "Legada", "restantes": "NaN"},
                {"restantes": "3"},
            ],
            "Historico": [{"data": "sem-data", "horas": "Infinity"}],
            "Questoes": [{"data": "2026-08-22", "feitas": "-3"}],
            "SessoesEstudo": [{"disciplina": "", "questoes": "9"}],
            "Erros": [{"status": "Aberto", "quantidade": "ruim"}],
        }
    )

    payload = build_study_workspace(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["cycle"]["totalHours"] == 0
    assert payload["cycle"]["subjects"][0]["environment"] == "Ambos"
    assert payload["missions"]["subjects"] == []
    assert payload["progress"]["totals"]["questions"] == 0
    assert payload["progress"]["subjects"] == []
    assert payload["progress"]["reviewPoints"][0]["subject"] == "Sem disciplina"


def test_personal_workspace_projects_daily_items_without_creating_logs():
    from api.personal import build_personal_workspace

    tables = empty_tables()
    tables.update(
        {
            "Tarefas": [
                {
                    "id": "t1",
                    "data": "2026-08-22",
                    "tarefa": "Revisar a lista",
                    "categoria": "Estudos",
                    "status": "Concluída",
                },
                {"id": "t2", "data": "2026-08-22", "status": "Pendente"},
                {
                    "data": "2026-08-22",
                    "tarefa": "Tarefa legada",
                    "categoria": "Pessoal",
                    "status": "Pendente",
                },
            ],
            "HabitosConfig": [
                {"id": "hc1", "nome": "Ler", "ativo": "Sim"},
                {"id": "hc2", "nome": "Alongar", "ativo": "Sim"},
                {"id": "hc3", "nome": "Arquivado", "ativo": "Não"},
            ],
            "Habitos": [
                {"id": "h1", "data": "2026-08-20", "habito": "Ler", "feito": "Sim"},
                {"id": "h2", "data": "2026-08-21", "habito": "Ler", "feito": "Sim"},
                {"id": "h3", "data": "2026-08-22", "habito": "Ler", "feito": "Sim"},
            ],
            "Leitura": [
                {
                    "id": "b1",
                    "titulo": "O homem que calculava",
                    "autor": "Malba Tahan",
                    "pagina_atual": "120",
                    "total_paginas": "240",
                    "meta_diaria": "20",
                    "status": "Lendo",
                }
            ],
            "Atividade": [
                {"id": "a1", "data": "2026-08-22", "tipo": "Corrida", "feito": "Sim"},
                {"id": "a2", "data": "2026-08-22", "feito": "Sim"},
            ],
        }
    )
    original = copy.deepcopy(tables)

    payload = build_personal_workspace(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert tables == original
    assert payload["tasks"]["total"] == 3
    assert payload["tasks"]["completed"] == 1
    assert payload["tasks"]["items"][1]["title"] == "Tarefa sem título"
    assert payload["tasks"]["items"][0]["mutable"] is True
    assert payload["tasks"]["items"][1]["mutable"] is True
    assert payload["tasks"]["items"][2] == {
        "id": "task-3",
        "title": "Tarefa legada",
        "category": "Pessoal",
        "completed": False,
        "mutable": False,
    }
    assert payload["habits"]["items"] == [
        {
            "configId": "hc1",
            "logId": "h3",
            "title": "Ler",
            "completed": True,
            "streakDays": 3,
            "mutable": True,
        },
        {
            "configId": "hc2",
            "logId": None,
            "title": "Alongar",
            "completed": False,
            "streakDays": 0,
            "mutable": True,
        },
    ]
    assert payload["reading"]["items"][0]["progress"] == 0.5
    assert payload["reading"]["items"][0]["remainingTarget"] == 20
    assert payload["activity"]["items"] == [
        {"id": "a1", "type": "Corrida", "completed": True}
    ]


def test_profile_workspace_calculates_achievements_without_persisting_them():
    from api.profile import build_profile_workspace

    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "0"}],
            "Historico": [
                {"data": f"2026-08-{day:02d}", "horas": "1"}
                for day in range(16, 23)
            ],
            "Questoes": [
                {"data": "2026-08-22", "feitas": "100", "acertos": "80", "erros": "20"}
            ],
            "Revisoes": [{"status": "Concluída"} for _ in range(10)],
            "Avaliacoes": [{"tipo": "Prova", "status": "Concluída"}],
            "Conquistas": [
                {
                    "id": "2",
                    "desbloqueada": "Não",
                    "data": "2026-08-09",
                },
                {"id": "11", "desbloqueada": "Sim", "data": "2026-08-10"}
            ],
            "Config": [
                {"disciplina": "Matemática", "horas": "5", "ambiente": "Mesa"}
            ],
            "Ciclo": [{"disciplina": "Matemática", "restantes": "2"}],
        }
    )
    original = copy.deepcopy(tables)

    payload = build_profile_workspace(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert tables == original
    assert payload["achievements"]["total"] == 11
    assert payload["achievements"]["unlocked"] == 7
    assert payload["achievements"]["items"][0]["unlocked"] is True
    assert payload["achievements"]["items"][1]["unlocked"] is False
    assert payload["achievements"]["items"][1]["unlockedAt"] is None
    assert payload["achievements"]["items"][-1]["unlocked"] is True
    assert payload["achievements"]["items"][-1]["unlockedAt"] == "2026-08-10"
    assert payload["settings"] == {
        "environments": ["Mesa", "Transporte", "Ambos"],
        "subjects": [
            {"discipline": "Matemática", "hours": 5.0, "environment": "Mesa"}
        ],
        "cycle": [{"discipline": "Matemática", "remainingHours": 2.0}],
    }
