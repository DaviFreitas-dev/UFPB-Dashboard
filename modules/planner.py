from datetime import date, timedelta

from modules.config import WEEKDAYS
from modules.database import (
    append_record,
    delete_record,
    new_id,
    records,
    update_record,
)
from modules.gamification import award_xp_once
from modules.questions import questions_between


def monday_of(target=None):
    target = target or date.today()
    return target - timedelta(days=target.weekday())


def add_weekly(day_name, time_text, activity, category):
    append_record(
        "AgendaSemanal",
        [new_id(), day_name, time_text, activity, category, "Sim"],
    )


def weekly_items(active_only=True):
    rows = records("AgendaSemanal")
    if active_only:
        rows = [row for row in rows if row.get("ativo") == "Sim"]
    return rows


def weekly_for_date(target_date):
    day_name = WEEKDAYS[target_date.weekday()]
    return [
        row
        for row in weekly_items()
        if row.get("dia_semana") == day_name
    ]


def archive_weekly(item_id):
    return update_record("AgendaSemanal", item_id, {"ativo": "Não"})


def checkins_for_date(target_date):
    target = str(target_date)
    return {
        str(row.get("agenda_id")): row
        for row in records("AgendaCheckins")
        if str(row.get("data")) == target
    }


def toggle_weekly(item_id, target_date, done):
    target = str(target_date)
    rows = records("AgendaCheckins")
    existing = next(
        (
            row for row in rows
            if str(row.get("agenda_id")) == str(item_id)
            and str(row.get("data")) == target
        ),
        None,
    )

    status = "Concluída" if done else "Pendente"

    if existing:
        update_record("AgendaCheckins", existing["id"], {"status": status})
    else:
        append_record(
            "AgendaCheckins",
            [new_id(), target, item_id, status],
        )

    if done:
        award_xp_once(
            f"agenda:{item_id}:{target}",
            10,
            "rotina",
            "Atividade fixa concluída",
        )


def add_assessment(title, kind, subject, target_date, question_goal=0):
    append_record(
        "Avaliacoes",
        [
            new_id(),
            title,
            kind,
            subject,
            str(target_date),
            int(question_goal),
            "Pendente",
        ],
    )


def assessments(include_done=False):
    rows = records("Avaliacoes")

    if not include_done:
        rows = [row for row in rows if row.get("status") != "Concluída"]

    def sort_key(row):
        try:
            return date.fromisoformat(str(row.get("data")))
        except ValueError:
            return date.max

    return sorted(rows, key=sort_key)


def complete_assessment(item_id):
    updated = update_record("Avaliacoes", item_id, {"status": "Concluída"})
    if updated:
        award_xp_once(
            f"assessment:{item_id}",
            75,
            "prazo",
            "Avaliação ou entrega concluída",
        )
    return updated


def remove_assessment(item_id):
    return delete_record("Avaliacoes", item_id)


def schedule_reviews(discipline, topic, origin, base_date=None):
    base = base_date or date.today()
    topic = topic.strip() or "Revisão geral"
    existing = records("Revisoes")

    for days in (1, 7, 30):
        review_date = base + timedelta(days=days)
        review_origin = f"{origin}:{days}"

        if any(
            str(row.get("origem")) == review_origin
            for row in existing
        ):
            continue

        append_record(
            "Revisoes",
            [
                new_id(),
                str(base),
                str(review_date),
                discipline,
                topic,
                "Pendente",
                review_origin,
            ],
        )


def due_reviews(target=None, include_future=False):
    target = target or date.today()
    rows = []

    for row in records("Revisoes"):
        if row.get("status") == "Concluída":
            continue

        try:
            review_date = date.fromisoformat(str(row.get("data")))
        except ValueError:
            continue

        if include_future or review_date <= target:
            rows.append(row)

    return sorted(rows, key=lambda row: str(row.get("data")))


def complete_review(item_id):
    updated = update_record("Revisoes", item_id, {"status": "Concluída"})
    if updated:
        award_xp_once(
            f"review:{item_id}",
            20,
            "revisao",
            "Revisão concluída",
        )
    return updated


def add_error(discipline, topic, quantity, note):
    append_record(
        "Erros",
        [
            new_id(),
            str(date.today()),
            discipline,
            topic.strip() or "Não informado",
            int(quantity),
            note.strip(),
            "Aberto",
        ],
    )


def open_errors():
    return [
        row
        for row in records("Erros")
        if row.get("status") != "Resolvido"
    ]


def resolve_error(item_id):
    updated = update_record("Erros", item_id, {"status": "Resolvido"})
    if updated:
        award_xp_once(
            f"error:{item_id}:resolved",
            15,
            "erros",
            "Erro revisado e resolvido",
        )
    return updated


def current_week_goal(default=200):
    start = monday_of()
    end = start + timedelta(days=6)
    rows = records("Metas")

    existing = next(
        (
            row
            for row in rows
            if row.get("tipo") == "questoes_semana"
            and str(row.get("inicio")) == str(start)
        ),
        None,
    )

    if not existing:
        append_record(
            "Metas",
            [
                new_id(),
                "questoes_semana",
                str(start),
                str(end),
                int(default),
                "Ativa",
            ],
        )
        rows = records("Metas")
        existing = next(
            row
            for row in rows
            if row.get("tipo") == "questoes_semana"
            and str(row.get("inicio")) == str(start)
        )

    return existing


def set_weekly_question_goal(target):
    goal = current_week_goal()
    update_record("Metas", goal["id"], {"alvo": max(1, int(target))})
    return current_week_goal()


def weekly_goal_progress():
    goal = current_week_goal()
    start = date.fromisoformat(str(goal["inicio"]))
    end = date.fromisoformat(str(goal["fim"]))
    stats = questions_between(start, end)
    target = max(1, int(goal.get("alvo", 1) or 1))
    reached = stats["total"] >= target

    if reached:
        award_xp_once(
            f"goal:questions:{start}",
            100,
            "meta",
            "Meta semanal de questões alcançada",
        )

    return {
        "target": target,
        "done": stats["total"],
        "progress": min(stats["total"] / target, 1.0),
        "reached": reached,
        "start": start,
        "end": end,
    }


def priorities_for_date(target_date):
    target = str(target_date)
    return [
        row
        for row in records("Planejamento")
        if str(row.get("data")) == target
    ]


def add_priority(target_date, text):
    existing = priorities_for_date(target_date)
    if len(existing) >= 3:
        return False

    append_record(
        "Planejamento",
        [new_id(), str(target_date), text, "Pendente"],
    )
    return True


def toggle_priority(item_id, done):
    updated = update_record(
        "Planejamento",
        item_id,
        {"status": "Concluída" if done else "Pendente"},
    )

    if updated and done:
        award_xp_once(
            f"priority:{item_id}",
            10,
            "planejamento",
            "Prioridade concluída",
        )

    return updated


def add_journal(text, target_date=None):
    target = target_date or date.today()
    append_record("Diario", [new_id(), str(target), text.strip()])


def journal_entries(limit=20):
    rows = sorted(
        records("Diario"),
        key=lambda row: str(row.get("data")),
        reverse=True,
    )
    return rows[:limit]


def weekly_summary(reference=None):
    reference = reference or date.today()
    start = monday_of(reference)
    end = start + timedelta(days=6)

    hours = 0
    for row in records("Historico"):
        try:
            day = date.fromisoformat(str(row.get("data")))
            if start <= day <= end:
                hours += int(row.get("horas", 0) or 0)
        except (TypeError, ValueError):
            continue

    q = questions_between(start, end)

    tasks_done = 0
    for row in records("Tarefas"):
        try:
            day = date.fromisoformat(str(row.get("data")))
            if start <= day <= end and row.get("status") == "Concluída":
                tasks_done += 1
        except ValueError:
            continue

    habits_done = 0
    for row in records("Habitos"):
        try:
            day = date.fromisoformat(str(row.get("data")))
            if start <= day <= end and row.get("feito") == "Sim":
                habits_done += 1
        except ValueError:
            continue

    reviews_done = 0
    for row in records("Revisoes"):
        if row.get("status") != "Concluída":
            continue
        try:
            created = date.fromisoformat(str(row.get("data")))
            if start <= created <= end:
                reviews_done += 1
        except ValueError:
            continue

    return {
        "start": start,
        "end": end,
        "hours": hours,
        "questions": q["total"],
        "accuracy": q["accuracy"],
        "tasks": tasks_done,
        "habits": habits_done,
        "reviews": reviews_done,
    }
