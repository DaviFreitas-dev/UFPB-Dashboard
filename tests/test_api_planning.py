import copy
from datetime import date

from api.planning import build_planning_dashboard
from api.sheets import DASHBOARD_SHEETS


def empty_tables():
    return {name: [] for name in DASHBOARD_SHEETS}


def test_planning_adapts_current_data_without_mutating_tables():
    tables = empty_tables()
    tables.update(
        {
            "Usuario": [{"chave": "xp", "valor": "3420"}],
            "Historico": [
                {"data": "2026-08-18", "horas": "1.5"},
                {"data": "2026-08-20", "horas": "2"},
            ],
            "Questoes": [
                {
                    "data": "2026-08-19",
                    "feitas": "40",
                    "acertos": "30",
                }
            ],
            "AgendaSemanal": [
                {
                    "id": "a1",
                    "dia_semana": "Segunda",
                    "hora": "08:00",
                    "atividade": "Aula de Física",
                    "categoria": "Escola",
                    "ativo": "Sim",
                },
                {
                    "id": "a2",
                    "dia_semana": "Segunda",
                    "hora": "18:00",
                    "atividade": "Atividade arquivada",
                    "ativo": "Não",
                },
            ],
            "Avaliacoes": [
                {
                    "id": "av1",
                    "titulo": "Simulado",
                    "tipo": "Prova",
                    "disciplina": "Física",
                    "data": "2026-08-27",
                    "meta_questoes": "50",
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
            "Revisoes": [
                {
                    "id": "r1",
                    "data": "2026-08-21",
                    "disciplina": "Matemática",
                    "assunto": "Funções",
                    "status": "Pendente",
                },
                {
                    "id": "r2",
                    "data": "2026-08-20",
                    "status": "Concluída",
                },
            ],
            "Erros": [
                {
                    "id": "e1",
                    "disciplina": "Química",
                    "assunto": "Estequiometria",
                    "quantidade": "3",
                    "nota": "Rever proporções",
                    "status": "Aberto",
                }
            ],
            "Planejamento": [
                {
                    "id": "p1",
                    "data": "2026-08-23",
                    "prioridade": "Terminar a lista",
                    "status": "Pendente",
                }
            ],
            "Tarefas": [
                {
                    "data": "2026-08-20",
                    "status": "Concluída",
                }
            ],
            "Diario": [
                {
                    "id": "d1",
                    "data": "2026-08-22",
                    "texto": "Funções ficaram mais claras hoje.",
                }
            ],
        }
    )
    original = copy.deepcopy(tables)

    payload = build_planning_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert tables == original
    assert payload["user"]["level"] == 4
    assert payload["summary"] == {
        "start": "2026-08-17",
        "end": "2026-08-23",
        "studyHours": 3.5,
        "questions": 40,
        "accuracy": 0.75,
        "tasksCompleted": 1,
        "reviewsCompleted": 1,
    }
    assert payload["weeklyQuestions"]["target"] == 200
    assert payload["week"][0]["items"][0]["title"] == "Aula de Física"
    assert payload["week"][5]["isToday"] is True
    assert payload["assessments"][0]["isBoss"] is True
    assert payload["reviews"][0]["topic"] == "Funções"
    assert payload["weakPoints"][0]["quantity"] == 3
    assert payload["tomorrow"][0]["title"] == "Terminar a lista"
    assert payload["journal"][0]["text"] == "Funções ficaram mais claras hoje."


def test_planning_tolerates_incomplete_legacy_rows():
    tables = empty_tables()
    tables.update(
        {
            "Historico": [
                {"data": "2026-08-20", "horas": "NaN"},
                {"data": "2026-08-21", "horas": "infinito"},
            ],
            "Questoes": [
                {"data": "2026-08-20", "feitas": "Infinity", "acertos": ""},
            ],
            "AgendaSemanal": [
                {"dia_semana": "Sábado", "ativo": "Sim"},
            ],
            "Avaliacoes": [{"data": "sem-data"}],
            "Erros": [{"status": "Aberto", "quantidade": "inválido"}],
            "Diario": [{"data": "sem-data", "texto": "ignorar"}],
        }
    )

    payload = build_planning_dashboard(
        tables,
        date(2026, 8, 22),
    ).model_dump(by_alias=True)

    assert payload["summary"]["studyHours"] == 0
    assert payload["week"][5]["items"][0]["title"] == "Atividade sem título"
    assert payload["assessments"] == []
    assert payload["weakPoints"][0]["quantity"] == 0
    assert payload["journal"] == []
