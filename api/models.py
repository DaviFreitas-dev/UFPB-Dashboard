from typing import Literal

from pydantic import BaseModel, ConfigDict


def _to_camel(value):
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


class DashboardUser(ApiModel):
    level: int
    xp: int
    xp_in_level: int
    xp_per_level: int
    xp_to_next_level: int
    streak_days: int
    longest_streak: int


class WeeklyGoal(ApiModel):
    completed: int
    target: int
    previous_week: int


class FocusItem(ApiModel):
    eyebrow: str
    title: str
    detail: str
    duration_minutes: int


class Deadline(ApiModel):
    kind: Literal["BOSS", "Prazo"]
    title: str
    subject: str
    date: str


class Review(ApiModel):
    id: str
    subject: str
    topic: str
    due_date: str


class Task(ApiModel):
    id: str
    title: str
    category: str
    completed: bool


class AgendaItem(Task):
    time: str


class Reading(ApiModel):
    title: str
    author: str
    current_page: int
    total_pages: int
    daily_target: int


class Habit(ApiModel):
    id: str
    title: str
    completed: bool


class ActivityDay(ApiModel):
    date: str
    minutes: int


class TodayDashboard(ApiModel):
    date: str
    user: DashboardUser
    weekly_questions: WeeklyGoal
    focus: FocusItem | None
    deadline: Deadline | None
    reviews: list[Review]
    priorities: list[Task]
    agenda: list[AgendaItem]
    tomorrow: list[Task]
    reading: Reading | None
    habits: list[Habit]
    physical_activity: str | None
    activity: list[ActivityDay]
