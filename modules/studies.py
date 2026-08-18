import random
from datetime import date, timedelta

from modules.config import XP_POR_HORA
from modules.database import (
    add_history,
    get_config,
    get_cycle,
    get_xp,
    set_xp,
    update_cycle,
)


def calculate_level(xp):
    level = xp // 1000 + 1
    xp_in_level = xp % 1000
    progress = xp_in_level / 1000
    missing = 1000 - xp_in_level
    return level, xp_in_level, progress, missing


def stats():
    rows = get_history()

    if not rows:
        return {
            "hours": 0,
            "average": 0,
            "best": 0,
            "days": 0,
            "streak": 0,
        }

    data = {}

    for row in rows:
        try:
            data[date.fromisoformat(row["data"])] = int(row["horas"])
        except Exception:
            continue

    if not data:
        return {
            "hours": 0,
            "average": 0,
            "best": 0,
            "days": 0,
            "streak": 0,
        }

    cursor = date.today()
    if cursor not in data:
        cursor -= timedelta(days=1)

    streak = 0
    while cursor in data and data[cursor] > 0:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "hours": sum(data.values()),
        "average": sum(data.values()) / len(data),
        "best": max(data.values()),
        "days": len(data),
        "streak": streak,
    }


def cycle_summary():
    config = get_config()
    cycle = get_cycle()
    total = sum(int(row["horas"]) for row in config)
    remaining = sum(int(row["restantes"]) for row in cycle)
    done = max(total - remaining, 0)
    progress = done / total if total else 0
    return total, remaining, done, progress


def draw_mission(hours, environment):
    cycle = get_cycle()
    config = {row["disciplina"]: row["ambiente"] for row in get_config()}

    available = {}
    for row in cycle:
        remaining = int(row["restantes"])
        subject = row["disciplina"]
        if remaining <= 0:
            continue

        env = config.get(subject, "Ambos")
        if environment in ("Ambos", env) or env == "Ambos":
            available[subject] = remaining

    if not available:
        return {}

    remaining_hours = hours
    mission = {}

    while remaining_hours > 0 and available:
        subject = random.choice(list(available.keys()))
        amount = random.randint(
            1,
            min(remaining_hours, available[subject]),
        )
        mission[subject] = mission.get(subject, 0) + amount
        remaining_hours -= amount
        available[subject] -= amount
        if available[subject] <= 0:
            del available[subject]

    return mission


def complete_mission(mission):
    hours = sum(mission.values())
    if hours <= 0:
        return 0, 0

    cycle = get_cycle()

    for row in cycle:
        if row["disciplina"] in mission:
            row["restantes"] = max(
                0,
                int(row["restantes"]) - mission[row["disciplina"]],
            )

    update_cycle(cycle)

    xp = hours * XP_POR_HORA
    set_xp(get_xp() + xp)
    add_history(hours, xp)

    return hours, xp
