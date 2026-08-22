import copy
from datetime import date

from api.dashboard import build_today_dashboard
from api.sheets import DASHBOARD_SHEETS


def empty_tables():
    return {name: [] for name in DASHBOARD_SHEETS}


def test_dashboard_adapts_current_data_without_mutating_tables():
    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "3420"}],
            "Historico": [{"data": "2026-08-17", "horas": "1", "xp": "100"}],
            "Questoes": [
                {"data": "2026-08-16", "feitas": "98"},
                {"data": "2026-08-22", "feitas": "126"},
            ],
            "SessoesEstudo": [
                {"data": f"2026-08-{day:02d}"}
                for day in range(18, 22)
            ],
            "Revisoes": [
                {
                    "id": "r1",
                    "data": "2026-08-22",
                    "disciplina": "Matemática",
                    "assunto": "Funções",
                    "status": "Pendente",
                },
                {
                    "id": "r2",
                    "data": "2026-08-23",
                    "disciplina": "Física",
                    "assunto": "Ondas",
                    "status": "Pendente",
                },
            ],
            "AgendaSemanal": [
                {
                    "id": "a1",
                    "dia_semana": "Sábado",
                    "hora": "09:00",
                    "atividade": "Curso",
                    "categoria": "Estudos",
                    "ativo": "Sim",
                }
            ],
            "AgendaCheckins": [
                {
                    "data": "2026-08-22",
                    "agenda_id": "a1",
                    "status": "Concluída",
                }
            ],
            "Avaliacoes": [
                {
                    "id": "boss1",
                    "titulo": "Simulado de Física",
                    "tipo": "Prova",
                    "disciplina": "Física",
                    "data": "2026-08-27",
                    "status": "Pendente",
                }
            ],
            "Metas": [
                {
                    "tipo": "questoes_semana",
                    "inicio": "2026-08-17",
                    "fim": "2026-08-23",
                    "alvo": "200",
                }
            ],
            "Planejamento": [
                {
                    "id": "p1",
                    "data": "2026-08-23",
                    "prioridade": "Terminar a lista de Física",
                    "status": "Pendente",
                }
            ],
            "Rotina": [
                {
                    "id": "rt1",
                    "data": "2026-08-22",
                    "hora": "18:30",
                    "atividade": "Academia",
                    "status": "Pendente",
                }
            ],
            "Tarefas": [
                {
                    "id": "t1",
                    "data": "2026-08-22",
                    "tarefa": "Resolver 30 questões",
                    "categoria": "Estudos",
                    "status": "Pendente",
                }
            ],
            "Leitura": [
                {
                    "titulo": "O homem que calculava",
                    "autor": "Malba Tahan",
                    "pagina_atual": "84",
                    "total_paginas": "240",
                    "meta_diaria": "20",
                    "status": "Lendo",
                }
            ],
            "HabitosConfig": [
                {"id": "hc1", "nome": "Ler 20 páginas", "ativo": "Sim"},
                {"id": "hc2", "nome": "Alongar", "ativo": "Sim"},
            ],
            "Habitos": [
                {
                    "id": "h1",
                    "data": "2026-08-22",
                    "habito": "Ler 20 páginas",
                    "feito": "Sim",
                }
            ],
            "Atividade": [
                {
                    "id": "at1",
                    "data": "2026-08-22",
                    "tipo": "Treino de força",
                    "feito": "Sim",
                }
            ],
        }
    )
    original = copy.deepcopy(tables)

    dashboard = build_today_dashboard(tables, date(2026, 8, 22))
    payload = dashboard.model_dump(by_alias=True)

    assert tables == original
    assert payload["date"] == "2026-08-22"
    assert payload["user"] == {
        "level": 4,
        "xp": 3420,
        "xpInLevel": 420,
        "xpPerLevel": 1000,
        "xpToNextLevel": 580,
        "streakDays": 6,
        "longestStreak": 6,
    }
    assert payload["weeklyQuestions"] == {
        "completed": 126,
        "target": 200,
        "previousWeek": 98,
    }
    assert payload["focus"]["title"] == "Revisar Funções"
    assert payload["deadline"]["kind"] == "BOSS"
    assert payload["agenda"][0]["completed"] is True
    assert payload["agenda"][1]["title"] == "Academia"
    assert payload["habits"][-1]["completed"] is False
    assert payload["physicalActivity"] == "Treino de força"
    assert payload["activity"][1]["minutes"] == 60


def test_dashboard_tolerates_incomplete_legacy_rows():
    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "inválido"}],
            "Historico": [{"data": "sem-data", "horas": ""}],
            "Tarefas": [{"data": "2026-08-22"}],
            "Leitura": [
                {
                    "titulo": "Livro legado",
                    "pagina_atual": "",
                    "total_paginas": "",
                    "status": "Lendo",
                }
            ],
            "Atividade": [{"data": "2026-08-22", "feito": "Sim"}],
        }
    )

    payload = build_today_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["user"]["xp"] == 0
    assert payload["priorities"][0]["title"] == "Tarefa sem título"
    assert payload["reading"]["totalPages"] == 1
    assert payload["physicalActivity"] is None
