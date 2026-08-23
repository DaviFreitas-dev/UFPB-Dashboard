from api.dashboard import (
    _completed,
    _equals,
    _integer,
    _number,
    _rows,
    _text,
    _today,
    _user,
)
from api.sheets import read_dashboard_tables
from api.workspace_models import (
    Achievement,
    AchievementCollection,
    ProfileWorkspace,
    SettingsCycleItem,
    SettingsSnapshot,
    SettingsSubject,
)
from modules.config import AMBIENTES


ACHIEVEMENTS = (
    ("1", "Primeiro passo", "Conclua sua primeira hora de estudo."),
    ("2", "10 horas", "Acumule 10 horas de estudo."),
    ("3", "50 horas", "Acumule 50 horas de estudo."),
    ("4", "100 questões", "Resolva 100 questões."),
    ("5", "500 questões", "Resolva 500 questões."),
    ("6", "1.000 questões", "Resolva 1.000 questões."),
    ("7", "Precisão", "Mantenha 80% de acerto em pelo menos 100 questões."),
    ("8", "Uma semana", "Mantenha uma sequência geral de 7 dias."),
    ("9", "Revisor", "Conclua 10 revisões programadas."),
    ("10", "Boss derrotado", "Conclua uma prova cadastrada."),
    ("11", "Nível alto", "Alcance 5.000 XP."),
)


def _achievement_status(tables, user):
    study_hours = sum(
        max(0, _number(row.get("horas")))
        for row in _rows(tables, "Historico")
    )
    questions = sum(
        max(0, _integer(row.get("feitas")))
        for row in _rows(tables, "Questoes")
    )
    correct = sum(
        max(0, _integer(row.get("acertos")))
        for row in _rows(tables, "Questoes")
    )
    accuracy = min(correct / questions, 1) if questions else 0
    reviews_done = sum(
        _completed(row.get("status"))
        for row in _rows(tables, "Revisoes")
    )
    bosses_done = sum(
        _completed(row.get("status")) and _equals(row.get("tipo"), "Prova")
        for row in _rows(tables, "Avaliacoes")
    )
    return {
        "1": study_hours >= 1,
        "2": study_hours >= 10,
        "3": study_hours >= 50,
        "4": questions >= 100,
        "5": questions >= 500,
        "6": questions >= 1000,
        "7": questions >= 100 and accuracy >= 0.8,
        "8": user.streak_days >= 7,
        "9": reviews_done >= 10,
        "10": bosses_done >= 1,
        "11": user.xp >= 5000,
    }


def _achievements(tables, user):
    persisted = {
        _text(row.get("id")): row
        for row in _rows(tables, "Conquistas")
        if _text(row.get("id"))
    }
    status = _achievement_status(tables, user)
    items = []
    for item_id, title, description in ACHIEVEMENTS:
        saved = persisted.get(item_id, {})
        unlocked = status[item_id] or _equals(saved.get("desbloqueada"), "Sim")
        unlocked_at = (_text(saved.get("data")) or None) if unlocked else None
        items.append(
            Achievement(
                id=item_id,
                title=title,
                description=description,
                unlocked=unlocked,
                unlocked_at=unlocked_at,
            )
        )
    return AchievementCollection(
        unlocked=sum(item.unlocked for item in items),
        total=len(items),
        items=items,
    )


def _settings(tables):
    subjects = []
    for row in _rows(tables, "Config"):
        discipline = _text(row.get("disciplina"))
        if not discipline:
            continue
        environment = _text(row.get("ambiente"), "Ambos")
        if environment not in AMBIENTES:
            environment = "Ambos"
        subjects.append(
            SettingsSubject(
                discipline=discipline,
                hours=max(0, _number(row.get("horas"))),
                environment=environment,
            )
        )

    cycle = []
    for row in _rows(tables, "Ciclo"):
        discipline = _text(row.get("disciplina"))
        if not discipline:
            continue
        cycle.append(
            SettingsCycleItem(
                discipline=discipline,
                remaining_hours=max(0, _number(row.get("restantes"))),
            )
        )
    return SettingsSnapshot(
        environments=list(AMBIENTES),
        subjects=subjects,
        cycle=cycle,
    )


def build_profile_workspace(tables, reference=None):
    reference = reference or _today()
    user = _user(tables, reference)
    return ProfileWorkspace(
        date=str(reference),
        user=user,
        achievements=_achievements(tables, user),
        settings=_settings(tables),
    )


def load_profile_workspace():
    return build_profile_workspace(read_dashboard_tables())
