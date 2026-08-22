import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from api.models import (
    ActivityDay,
    AgendaItem,
    DashboardUser,
    Deadline,
    FocusItem,
    Habit,
    Reading,
    Review,
    Task,
    TodayDashboard,
    WeeklyGoal,
)
from api.sheets import read_dashboard_tables
from modules.config import WEEKDAYS, XP_POR_NIVEL


def _today():
    timezone_name = os.getenv("NEXO_TIMEZONE", "America/Fortaleza")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise RuntimeError(f"Fuso horário inválido: {timezone_name}") from error
    return datetime.now(timezone).date()


def _rows(tables, name):
    rows = tables.get(name, [])
    return rows if isinstance(rows, list) else []


def _text(value, default=""):
    text = str(value or "").strip()
    return text or default


def _integer(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _date(value):
    try:
        return date.fromisoformat(_text(value))
    except ValueError:
        return None


def _equals(value, expected):
    return _text(value).casefold() == expected.casefold()


def _completed(value):
    return _text(value).casefold() in {"concluída", "concluida", "sim"}


def _row_id(row, prefix, index):
    return _text(row.get("id"), f"{prefix}-{index + 1}")


def _question_total(rows, start, end):
    total = 0
    for row in rows:
        day = _date(row.get("data"))
        if day is not None and start <= day <= end:
            total += max(0, _integer(row.get("feitas")))
    return total


def _weekly_goal(tables, reference):
    monday = reference - timedelta(days=reference.weekday())
    sunday = monday + timedelta(days=6)
    previous_monday = monday - timedelta(days=7)
    previous_sunday = monday - timedelta(days=1)

    goals = _rows(tables, "Metas")
    goal = next(
        (
            row
            for row in goals
            if _equals(row.get("tipo"), "questoes_semana")
            and _date(row.get("inicio")) == monday
        ),
        None,
    )
    questions = _rows(tables, "Questoes")
    return WeeklyGoal(
        completed=_question_total(questions, monday, sunday),
        target=max(1, _integer(goal.get("alvo"), 200) if goal else 200),
        previous_week=_question_total(
            questions,
            previous_monday,
            previous_sunday,
        ),
    )


def _active_days(tables):
    days = set()
    sources = (
        ("Historico", lambda row: _number(row.get("horas")) > 0),
        ("Tarefas", lambda row: _completed(row.get("status"))),
        ("Habitos", lambda row: _completed(row.get("feito"))),
        ("Atividade", lambda row: _completed(row.get("feito"))),
        ("AgendaCheckins", lambda row: _completed(row.get("status"))),
        ("SessoesEstudo", lambda row: True),
    )

    for sheet, predicate in sources:
        for row in _rows(tables, sheet):
            day = _date(row.get("data"))
            if day is not None and predicate(row):
                days.add(day)
    return days


def _streaks(active_days, reference):
    if not active_days:
        return 0, 0

    cursor = reference if reference in active_days else reference - timedelta(days=1)
    current = 0
    while cursor in active_days:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    run = 0
    previous = None
    for day in sorted(active_days):
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    return current, longest


def _user(tables, reference):
    xp_row = next(
        (
            row
            for row in _rows(tables, "Usuario")
            if _text(row.get("chave")) == "xp"
        ),
        None,
    )
    xp = max(0, _integer(xp_row.get("valor")) if xp_row else 0)
    level = xp // XP_POR_NIVEL + 1
    xp_in_level = xp % XP_POR_NIVEL
    current_streak, longest_streak = _streaks(
        _active_days(tables),
        reference,
    )
    return DashboardUser(
        level=level,
        xp=xp,
        xp_in_level=xp_in_level,
        xp_per_level=XP_POR_NIVEL,
        xp_to_next_level=XP_POR_NIVEL - xp_in_level,
        streak_days=current_streak,
        longest_streak=longest_streak,
    )


def _reviews(tables, reference):
    due = []
    for index, row in enumerate(_rows(tables, "Revisoes")):
        due_date = _date(row.get("data"))
        if _completed(row.get("status")) or due_date is None or due_date > reference:
            continue
        due.append(
            Review(
                id=_row_id(row, "review", index),
                subject=_text(row.get("disciplina"), "Sem disciplina"),
                topic=_text(row.get("assunto"), "Revisão geral"),
                due_date=str(due_date),
            )
        )
    return sorted(due, key=lambda item: (item.due_date, item.id))[:4]


def _tasks_for_date(tables, reference):
    result = []
    for index, row in enumerate(_rows(tables, "Tarefas")):
        if _date(row.get("data")) != reference:
            continue
        result.append(
            Task(
                id=_row_id(row, "task", index),
                title=_text(row.get("tarefa"), "Tarefa sem título"),
                category=_text(row.get("categoria"), "Outro"),
                completed=_completed(row.get("status")),
            )
        )
    return result


def _agenda(tables, reference):
    agenda = []
    checkins = {
        _text(row.get("agenda_id")): row
        for row in _rows(tables, "AgendaCheckins")
        if _date(row.get("data")) == reference
    }
    weekday = WEEKDAYS[reference.weekday()]

    for index, row in enumerate(_rows(tables, "AgendaSemanal")):
        if not _equals(row.get("ativo"), "Sim"):
            continue
        if not _equals(row.get("dia_semana"), weekday):
            continue
        item_id = _row_id(row, "weekly", index)
        agenda.append(
            AgendaItem(
                id=item_id,
                time=_text(row.get("hora"), "--:--"),
                title=_text(row.get("atividade"), "Atividade sem título"),
                category=_text(row.get("categoria"), "Agenda"),
                completed=_completed(checkins.get(item_id, {}).get("status")),
            )
        )

    for index, row in enumerate(_rows(tables, "Rotina")):
        if _date(row.get("data")) != reference:
            continue
        agenda.append(
            AgendaItem(
                id=_row_id(row, "routine", index),
                time=_text(row.get("hora"), "--:--"),
                title=_text(row.get("atividade"), "Atividade sem título"),
                category="Rotina",
                completed=_completed(row.get("status")),
            )
        )
    return sorted(agenda, key=lambda item: (item.time, item.id))


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
                category="Planejamento",
                completed=_completed(row.get("status")),
            )
        )
    return result[:3]


def _deadline(tables):
    valid = []
    for row in _rows(tables, "Avaliacoes"):
        target = _date(row.get("data"))
        if _completed(row.get("status")) or target is None:
            continue
        valid.append((target, row))
    if not valid:
        return None

    target, row = min(valid, key=lambda item: item[0])
    return Deadline(
        kind="BOSS" if _equals(row.get("tipo"), "Prova") else "Prazo",
        title=_text(row.get("titulo"), "Prazo sem título"),
        subject=_text(row.get("disciplina"), "Sem disciplina"),
        date=str(target),
    )


def _reading(tables):
    row = next(
        (
            item
            for item in _rows(tables, "Leitura")
            if _equals(item.get("status"), "Lendo")
        ),
        None,
    )
    if row is None:
        return None
    return Reading(
        title=_text(row.get("titulo"), "Livro sem título"),
        author=_text(row.get("autor"), "Autor não informado"),
        current_page=max(0, _integer(row.get("pagina_atual"))),
        total_pages=max(1, _integer(row.get("total_paginas"), 1)),
        daily_target=max(0, _integer(row.get("meta_diaria"))),
    )


def _habits(tables, reference):
    logs = {
        _text(row.get("habito")): row
        for row in _rows(tables, "Habitos")
        if _date(row.get("data")) == reference
    }
    result = []
    for index, config in enumerate(_rows(tables, "HabitosConfig")):
        if not _equals(config.get("ativo"), "Sim"):
            continue
        name = _text(config.get("nome"))
        if not name:
            continue
        log = logs.get(name, {})
        result.append(
            Habit(
                id=_text(log.get("id"), _row_id(config, "habit", index)),
                title=name,
                completed=_completed(log.get("feito")),
            )
        )
    return result


def _physical_activity(tables, reference):
    activities = []
    for row in _rows(tables, "Atividade"):
        if _date(row.get("data")) != reference or not _completed(row.get("feito")):
            continue
        activity = _text(row.get("tipo"))
        if activity and activity not in activities:
            activities.append(activity)
    return " · ".join(activities) if activities else None


def _activity(tables, reference):
    minutes_by_day = {}
    for row in _rows(tables, "Historico"):
        day = _date(row.get("data"))
        if day is None:
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0) + max(
            0,
            round(_number(row.get("horas")) * 60),
        )

    return [
        ActivityDay(
            date=str(reference + timedelta(days=offset)),
            minutes=minutes_by_day.get(reference + timedelta(days=offset), 0),
        )
        for offset in range(-6, 1)
    ]


def _focus(reviews, priorities, agenda):
    if reviews:
        review = reviews[0]
        return FocusItem(
            eyebrow="Revisão pendente",
            title=f"Revisar {review.topic}",
            detail=f"{review.subject} · prevista para {review.due_date}",
            duration_minutes=30,
        )

    pending_task = next((item for item in priorities if not item.completed), None)
    if pending_task:
        return FocusItem(
            eyebrow="Prioridade de hoje",
            title=pending_task.title,
            detail=pending_task.category,
            duration_minutes=30,
        )

    pending_agenda = next((item for item in agenda if not item.completed), None)
    if pending_agenda:
        return FocusItem(
            eyebrow="Próxima atividade",
            title=pending_agenda.title,
            detail=f"{pending_agenda.time} · {pending_agenda.category}",
            duration_minutes=30,
        )
    return None


def build_today_dashboard(tables, reference=None):
    reference = reference or _today()
    reviews = _reviews(tables, reference)
    priorities = _tasks_for_date(tables, reference)
    agenda = _agenda(tables, reference)

    return TodayDashboard(
        date=str(reference),
        user=_user(tables, reference),
        weekly_questions=_weekly_goal(tables, reference),
        focus=_focus(reviews, priorities, agenda),
        deadline=_deadline(tables),
        reviews=reviews,
        priorities=priorities,
        agenda=agenda,
        tomorrow=_tomorrow(tables, reference),
        reading=_reading(tables),
        habits=_habits(tables, reference),
        physical_activity=_physical_activity(tables, reference),
        activity=_activity(tables, reference),
    )


def load_today_dashboard():
    return build_today_dashboard(read_dashboard_tables())
