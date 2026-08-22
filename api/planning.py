from datetime import timedelta

from api.dashboard import (
    _completed,
    _date,
    _equals,
    _integer,
    _number,
    _row_id,
    _rows,
    _text,
    _today,
    _user,
    _weekly_goal,
)
from api.models import (
    JournalEntry,
    PlanningAgendaItem,
    PlanningAssessment,
    PlanningDashboard,
    PlanningDay,
    Review,
    Task,
    WeakPoint,
    WeeklySummary,
)
from api.sheets import read_dashboard_tables
from modules.config import WEEKDAYS


def _week_bounds(reference):
    start = reference - timedelta(days=reference.weekday())
    return start, start + timedelta(days=6)


def _summary(tables, reference):
    start, end = _week_bounds(reference)
    study_hours = sum(
        max(0, _number(row.get("horas")))
        for row in _rows(tables, "Historico")
        if (day := _date(row.get("data"))) is not None and start <= day <= end
    )

    questions = 0
    correct = 0
    for row in _rows(tables, "Questoes"):
        day = _date(row.get("data"))
        if day is None or not start <= day <= end:
            continue
        questions += max(0, _integer(row.get("feitas")))
        correct += max(0, _integer(row.get("acertos")))

    tasks_completed = sum(
        1
        for row in _rows(tables, "Tarefas")
        if (day := _date(row.get("data"))) is not None
        and start <= day <= end
        and _completed(row.get("status"))
    )
    reviews_completed = sum(
        1
        for row in _rows(tables, "Revisoes")
        if (day := _date(row.get("data"))) is not None
        and start <= day <= end
        and _completed(row.get("status"))
    )

    return WeeklySummary(
        start=str(start),
        end=str(end),
        study_hours=round(study_hours, 1),
        questions=questions,
        accuracy=round(min(correct / questions, 1), 4) if questions else 0,
        tasks_completed=tasks_completed,
        reviews_completed=reviews_completed,
    )


def _week(tables, reference):
    start, _ = _week_bounds(reference)
    weekly_rows = [
        row
        for row in _rows(tables, "AgendaSemanal")
        if _equals(row.get("ativo"), "Sim")
    ]
    result = []

    for offset, weekday in enumerate(WEEKDAYS):
        current_date = start + timedelta(days=offset)
        items = []
        for index, row in enumerate(weekly_rows):
            if not _equals(row.get("dia_semana"), weekday):
                continue
            items.append(
                PlanningAgendaItem(
                    id=_row_id(row, f"weekly-{offset}", index),
                    time=_text(row.get("hora"), "--:--"),
                    title=_text(row.get("atividade"), "Atividade sem título"),
                    category=_text(row.get("categoria"), "Agenda"),
                )
            )
        result.append(
            PlanningDay(
                name=weekday,
                date=str(current_date),
                is_today=current_date == reference,
                items=sorted(items, key=lambda item: (item.time, item.id)),
            )
        )
    return result


def _assessments(tables):
    result = []
    for index, row in enumerate(_rows(tables, "Avaliacoes")):
        target = _date(row.get("data"))
        if target is None or _completed(row.get("status")):
            continue
        kind = _text(row.get("tipo"), "Prazo")
        result.append(
            PlanningAssessment(
                id=_row_id(row, "assessment", index),
                title=_text(row.get("titulo"), "Prazo sem título"),
                kind=kind,
                subject=_text(row.get("disciplina"), "Sem disciplina"),
                date=str(target),
                question_goal=max(0, _integer(row.get("meta_questoes"))),
                is_boss=_equals(kind, "Prova"),
            )
        )
    return sorted(result, key=lambda item: (item.date, item.id))


def _due_reviews(tables, reference):
    result = []
    for index, row in enumerate(_rows(tables, "Revisoes")):
        target = _date(row.get("data"))
        if target is None or target > reference or _completed(row.get("status")):
            continue
        result.append(
            Review(
                id=_row_id(row, "review", index),
                subject=_text(row.get("disciplina"), "Sem disciplina"),
                topic=_text(row.get("assunto"), "Revisão geral"),
                due_date=str(target),
            )
        )
    return sorted(result, key=lambda item: (item.due_date, item.id))


def _weak_points(tables):
    result = []
    for index, row in enumerate(_rows(tables, "Erros")):
        if _equals(row.get("status"), "Resolvido"):
            continue
        result.append(
            WeakPoint(
                id=_row_id(row, "error", index),
                subject=_text(row.get("disciplina"), "Sem disciplina"),
                topic=_text(row.get("assunto"), "Assunto não informado"),
                quantity=max(0, _integer(row.get("quantidade"))),
                note=_text(row.get("nota")),
            )
        )
    return result


def _tomorrow(tables, reference):
    target = reference + timedelta(days=1)
    result = []
    for index, row in enumerate(_rows(tables, "Planejamento")):
        if _date(row.get("data")) != target:
            continue
        result.append(
            Task(
                id=_row_id(row, "tomorrow", index),
                title=_text(row.get("prioridade"), "Prioridade sem título"),
                category="Amanhã",
                completed=_completed(row.get("status")),
            )
        )
    return result[:3]


def _journal(tables):
    entries = []
    for index, row in enumerate(_rows(tables, "Diario")):
        entry_date = _date(row.get("data"))
        text = _text(row.get("texto"))
        if entry_date is None or not text:
            continue
        entries.append(
            JournalEntry(
                id=_row_id(row, "journal", index),
                date=str(entry_date),
                text=text,
            )
        )
    return sorted(entries, key=lambda item: (item.date, item.id), reverse=True)[:5]


def build_planning_dashboard(tables, reference=None):
    reference = reference or _today()
    return PlanningDashboard(
        date=str(reference),
        user=_user(tables, reference),
        summary=_summary(tables, reference),
        weekly_questions=_weekly_goal(tables, reference),
        week=_week(tables, reference),
        assessments=_assessments(tables),
        reviews=_due_reviews(tables, reference),
        weak_points=_weak_points(tables),
        tomorrow=_tomorrow(tables, reference),
        journal=_journal(tables),
    )


def load_planning_dashboard():
    return build_planning_dashboard(read_dashboard_tables())
