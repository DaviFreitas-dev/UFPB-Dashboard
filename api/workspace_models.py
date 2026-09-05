from api.models import ApiModel, DashboardUser, Task


class CycleSubject(ApiModel):
    id: str
    subject: str
    environment: str
    planned_hours: float
    remaining_hours: float
    completed_hours: float
    progress: float
    legacy: bool


class CycleSnapshot(ApiModel):
    total_hours: float
    remaining_hours: float
    completed_hours: float
    progress: float
    subjects: list[CycleSubject]


class MissionSubject(ApiModel):
    id: str
    subject: str
    environment: str
    remaining_hours: float


class MissionAvailability(ApiModel):
    duration_options: list[int]
    total_available_hours: float
    subjects: list[MissionSubject]


class ProgressTotals(ApiModel):
    study_hours: float
    questions: int
    correct: int
    wrong: int
    accuracy: float
    streak_days: int


class ProgressWeek(ApiModel):
    start: str
    end: str
    study_hours: float
    questions: int
    accuracy: float
    tasks_completed: int
    reviews_completed: int


class StudyHistoryPoint(ApiModel):
    date: str
    hours: float


class WeeklyAccuracyPoint(ApiModel):
    week_start: str
    questions: int
    accuracy: float


class SubjectProgress(ApiModel):
    subject: str
    questions: int
    correct: int
    wrong: int
    accuracy: float
    study_hours: float


class ReviewPoint(ApiModel):
    subject: str
    topic: str
    quantity: int


class ProgressSnapshot(ApiModel):
    totals: ProgressTotals
    week: ProgressWeek
    study_history: list[StudyHistoryPoint]
    weekly_accuracy: list[WeeklyAccuracyPoint]
    subjects: list[SubjectProgress]
    review_points: list[ReviewPoint]


class StudyWorkspace(ApiModel):
    date: str
    user: DashboardUser
    cycle: CycleSnapshot
    missions: MissionAvailability
    progress: ProgressSnapshot


class PersonalTask(Task):
    mutable: bool


class TaskCollection(ApiModel):
    total: int
    completed: int
    items: list[PersonalTask]


class PersonalHabit(ApiModel):
    config_id: str
    log_id: str | None
    title: str
    completed: bool
    streak_days: int


class HabitCollection(ApiModel):
    total: int
    completed: int
    items: list[PersonalHabit]


class ReadingBook(ApiModel):
    id: str
    title: str
    author: str
    current_page: int
    total_pages: int
    daily_target: int
    remaining_target: int
    status: str
    progress: float
    mutable: bool


class ReadingCollection(ApiModel):
    items: list[ReadingBook]


class PhysicalActivity(ApiModel):
    id: str
    type: str
    completed: bool


class ActivityCollection(ApiModel):
    items: list[PhysicalActivity]


class PersonalWorkspace(ApiModel):
    date: str
    user: DashboardUser
    tasks: TaskCollection
    habits: HabitCollection
    reading: ReadingCollection
    activity: ActivityCollection


class Achievement(ApiModel):
    id: str
    title: str
    description: str
    unlocked: bool
    unlocked_at: str | None


class AchievementCollection(ApiModel):
    unlocked: int
    total: int
    items: list[Achievement]


class SettingsSubject(ApiModel):
    discipline: str
    hours: float
    environment: str


class SettingsCycleItem(ApiModel):
    discipline: str
    remaining_hours: float


class SettingsSnapshot(ApiModel):
    environments: list[str]
    subjects: list[SettingsSubject]
    cycle: list[SettingsCycleItem]


class ProfileWorkspace(ApiModel):
    date: str
    user: DashboardUser
    achievements: AchievementCollection
    settings: SettingsSnapshot
