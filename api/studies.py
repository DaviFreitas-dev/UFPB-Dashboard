from datetime import timedelta

from api.dashboard import (
    _completed,
    _date,
    _integer,
    _number,
    _rows,
    _text,
    _today,
    _user,
)
from api.sheets import read_dashboard_tables
from api.workspace_models import (
    CycleSnapshot,
    CycleSubject,
    MissionAvailability,
    MissionSubject,
    ProgressSnapshot,
    ProgressTotals,
    ProgressWeek,
    ReviewPoint,
    StudyHistoryPoint,
    StudyWorkspace,
    SubjectProgress,
    WeeklyAccuracyPoint,
)
from modules.config import AMBIENTES


def _ratio(value, total):
    return min(max(value / total, 0), 1) if total else 0


def _cycle(tables):
    config = {}
    order = []
    for row in _rows(tables, "Config"):
        subject = _text(row.get("disciplina"))
        if not subject or subject in config:
            continue
        environment = _text(row.get("ambiente"), "Ambos")
        if environment not in AMBIENTES:
            environment = "Ambos"
        config[subject] = {
            "hours": max(0, _number(row.get("horas"))),
            "environment": environment,
        }
        order.append(subject)

    remaining = {}
    for row in _rows(tables, "Ciclo"):
        subject = _text(row.get("disciplina"))
        if not subject:
            continue
        if subject not in remaining and subject not in config:
            order.append(subject)
        remaining[subject] = remaining.get(subject, 0) + max(
            0,
            _number(row.get("restantes")),
        )

    subjects = []
    for index, subject in enumerate(order):
        legacy = subject not in config
        configured = config.get(subject, {})
        planned = configured.get("hours", remaining.get(subject, 0))
        pending = remaining.get(subject, planned)
        completed = max(planned - pending, 0)
        subjects.append(
            CycleSubject(
                id=f"cycle-{index + 1}",
                subject=subject,
                environment=configured.get("environment", "Ambos"),
                planned_hours=planned,
                remaining_hours=pending,
                completed_hours=completed,
                progress=_ratio(completed, planned),
                legacy=legacy,
            )
        )

    total = sum(item.planned_hours for item in subjects)
    pending = sum(item.remaining_hours for item in subjects)
    completed = sum(item.completed_hours for item in subjects)
    return CycleSnapshot(
        total_hours=total,
        remaining_hours=pending,
        completed_hours=completed,
        progress=_ratio(completed, total),
        subjects=subjects,
    )


def _missions(cycle):
    subjects = [
        MissionSubject(
            id=item.id,
            subject=item.subject,
            environment=item.environment,
            remaining_hours=item.remaining_hours,
        )
        for item in cycle.subjects
        if item.remaining_hours > 0
    ]
    return MissionAvailability(
        duration_options=list(range(1, 7)),
        total_available_hours=sum(item.remaining_hours for item in subjects),
        subjects=subjects,
    )


def _history(tables):
    hours_by_day = {}
    for row in _rows(tables, "Historico"):
        day = _date(row.get("data"))
        hours = max(0, _number(row.get("horas")))
        if day is None or hours <= 0:
            continue
        hours_by_day[day] = hours_by_day.get(day, 0) + hours
    return hours_by_day


def _question_totals(rows, start=None, end=None):
    questions = correct = wrong = 0
    for row in rows:
        day = _date(row.get("data"))
        if start is not None and (day is None or not start <= day <= end):
            continue
        questions += max(0, _integer(row.get("feitas")))
        correct += max(0, _integer(row.get("acertos")))
        wrong += max(0, _integer(row.get("erros")))
    return questions, correct, wrong


def _subject_progress(tables):
    buckets = {}
    for row in _rows(tables, "SessoesEstudo"):
        subject = _text(row.get("disciplina"))
        if not subject:
            continue
        bucket = buckets.setdefault(
            subject,
            {"hours": 0.0, "questions": 0, "correct": 0, "wrong": 0},
        )
        bucket["hours"] += max(0, _number(row.get("horas")))
        bucket["questions"] += max(0, _integer(row.get("questoes")))
        bucket["correct"] += max(0, _integer(row.get("acertos")))
        bucket["wrong"] += max(0, _integer(row.get("erros")))

    return [
        SubjectProgress(
            subject=subject,
            questions=values["questions"],
            correct=values["correct"],
            wrong=values["wrong"],
            accuracy=_ratio(values["correct"], values["questions"]),
            study_hours=values["hours"],
        )
        for subject, values in sorted(buckets.items())
    ]


def _review_points(tables):
    buckets = {}
    for row in _rows(tables, "Erros"):
        if _text(row.get("status")).casefold() == "resolvido":
            continue
        key = (
            _text(row.get("disciplina"), "Sem disciplina"),
            _text(row.get("assunto"), "Assunto não informado"),
        )
        buckets[key] = buckets.get(key, 0) + max(
            0,
            _integer(row.get("quantidade")),
        )
    return [
        ReviewPoint(subject=subject, topic=topic, quantity=quantity)
        for (subject, topic), quantity in sorted(
            buckets.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _progress(tables, reference, user):
    history = _history(tables)
    question_rows = _rows(tables, "Questoes")
    questions, correct, wrong = _question_totals(question_rows)
    monday = reference - timedelta(days=reference.weekday())
    sunday = monday + timedelta(days=6)
    week_questions, week_correct, _ = _question_totals(
        question_rows,
        monday,
        sunday,
    )

    weekly_accuracy = []
    for offset in reversed(range(8)):
        start = monday - timedelta(weeks=offset)
        end = start + timedelta(days=6)
        total, right, _ = _question_totals(question_rows, start, end)
        weekly_accuracy.append(
            WeeklyAccuracyPoint(
                week_start=str(start),
                questions=total,
                accuracy=_ratio(right, total),
            )
        )

    return ProgressSnapshot(
        totals=ProgressTotals(
            study_hours=sum(history.values()),
            questions=questions,
            correct=correct,
            wrong=wrong,
            accuracy=_ratio(correct, questions),
            streak_days=user.streak_days,
        ),
        week=ProgressWeek(
            start=str(monday),
            end=str(sunday),
            study_hours=sum(
                hours for day, hours in history.items() if monday <= day <= sunday
            ),
            questions=week_questions,
            accuracy=_ratio(week_correct, week_questions),
            tasks_completed=sum(
                1
                for row in _rows(tables, "Tarefas")
                if (day := _date(row.get("data"))) is not None
                and monday <= day <= sunday
                and _completed(row.get("status"))
            ),
            reviews_completed=sum(
                1
                for row in _rows(tables, "Revisoes")
                if (day := _date(row.get("data"))) is not None
                and monday <= day <= sunday
                and _completed(row.get("status"))
            ),
        ),
        study_history=[
            StudyHistoryPoint(date=str(day), hours=hours)
            for day, hours in sorted(history.items())
        ],
        weekly_accuracy=weekly_accuracy,
        subjects=_subject_progress(tables),
        review_points=_review_points(tables),
    )


def build_study_workspace(tables, reference=None):
    reference = reference or _today()
    user = _user(tables, reference)
    cycle = _cycle(tables)
    return StudyWorkspace(
        date=str(reference),
        user=user,
        cycle=cycle,
        missions=_missions(cycle),
        progress=_progress(tables, reference, user),
    )


def load_study_workspace():
    return build_study_workspace(read_dashboard_tables())
