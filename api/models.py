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
    id: str
    title: str
    author: str
    current_page: int
    total_pages: int
    daily_target: int
    mutable: bool


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


class WeeklySummary(ApiModel):
    start: str
    end: str
    study_hours: float
    questions: int
    accuracy: float
    tasks_completed: int
    reviews_completed: int


class PlanningAgendaItem(ApiModel):
    id: str
    time: str
    title: str
    category: str


class PlanningDay(ApiModel):
    name: str
    date: str
    is_today: bool
    items: list[PlanningAgendaItem]


class PlanningAssessment(ApiModel):
    id: str
    title: str
    kind: str
    subject: str
    date: str
    question_goal: int
    is_boss: bool


class WeakPoint(ApiModel):
    id: str
    subject: str
    topic: str
    quantity: int
    note: str


class JournalEntry(ApiModel):
    id: str
    date: str
    text: str


class PlanningDashboard(ApiModel):
    date: str
    user: DashboardUser
    summary: WeeklySummary
    weekly_questions: WeeklyGoal
    week: list[PlanningDay]
    assessments: list[PlanningAssessment]
    reviews: list[Review]
    weak_points: list[WeakPoint]
    tomorrow: list[Task]
    journal: list[JournalEntry]


class RoutineItem(ApiModel):
    id: str
    source_id: str
    time: str
    title: str
    category: str
    kind: Literal["fixed", "custom"]
    completed: bool
    mutable: bool


class RoutineDashboard(ApiModel):
    date: str
    user: DashboardUser
    total: int
    completed: int
    fixed_count: int
    custom_count: int
    items: list[RoutineItem]
