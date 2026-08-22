export type DashboardUser = {
  level: number;
  xp: number;
  xpInLevel: number;
  xpPerLevel: number;
  xpToNextLevel: number;
  streakDays: number;
  longestStreak: number;
};

export type WeeklyGoal = {
  completed: number;
  target: number;
  previousWeek: number;
};

export type FocusItem = {
  eyebrow: string;
  title: string;
  detail: string;
  durationMinutes: number;
};

export type Deadline = {
  kind: "BOSS" | "Prazo";
  title: string;
  subject: string;
  date: string;
};

export type Review = {
  id: string;
  subject: string;
  topic: string;
  dueDate: string;
};

export type Task = {
  id: string;
  title: string;
  category: string;
  completed: boolean;
};

export type AgendaItem = {
  id: string;
  time: string;
  title: string;
  category: string;
  completed: boolean;
};

export type Reading = {
  title: string;
  author: string;
  currentPage: number;
  totalPages: number;
  dailyTarget: number;
};

export type Habit = {
  id: string;
  title: string;
  completed: boolean;
};

export type ActivityDay = {
  date: string;
  minutes: number;
};

export type TodayDashboard = {
  date: string;
  user: DashboardUser;
  weeklyQuestions: WeeklyGoal;
  focus: FocusItem | null;
  deadline: Deadline | null;
  reviews: Review[];
  priorities: Task[];
  agenda: AgendaItem[];
  tomorrow: Task[];
  reading: Reading | null;
  habits: Habit[];
  physicalActivity: string | null;
  activity: ActivityDay[];
};

export type DashboardResult = {
  dashboard: TodayDashboard;
  source: "api" | "demo";
};

export function ratio(completed: number, target: number): number {
  if (target <= 0) {
    return 0;
  }

  return Math.min(Math.max(completed / target, 0), 1);
}

export function formatDatePtBr(value: string): string {
  const date = new Date(`${value}T12:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export function deadlineLabel(deadline: string, reference: string): string {
  const targetDate = new Date(`${deadline}T12:00:00`);
  const referenceDate = new Date(`${reference}T12:00:00`);

  if (Number.isNaN(targetDate.getTime()) || Number.isNaN(referenceDate.getTime())) {
    return deadline;
  }

  const days = Math.round(
    (targetDate.getTime() - referenceDate.getTime()) / 86_400_000,
  );

  if (days === 0) {
    return "hoje";
  }

  if (days === 1) {
    return "amanhã";
  }

  if (days > 1) {
    return `em ${days} dias`;
  }

  const overdue = Math.abs(days);
  return `${overdue} ${overdue === 1 ? "dia" : "dias"} em atraso`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

function isArrayOf<T>(
  value: unknown,
  guard: (item: unknown) => item is T,
): value is T[] {
  return Array.isArray(value) && value.every(guard);
}

function isDashboardUser(value: unknown): value is DashboardUser {
  return (
    isRecord(value) &&
    isNumber(value.level) &&
    isNumber(value.xp) &&
    isNumber(value.xpInLevel) &&
    isNumber(value.xpPerLevel) &&
    isNumber(value.xpToNextLevel) &&
    isNumber(value.streakDays) &&
    isNumber(value.longestStreak)
  );
}

function isWeeklyGoal(value: unknown): value is WeeklyGoal {
  return (
    isRecord(value) &&
    isNumber(value.completed) &&
    isNumber(value.target) &&
    isNumber(value.previousWeek)
  );
}

function isFocusItem(value: unknown): value is FocusItem {
  return (
    isRecord(value) &&
    isString(value.eyebrow) &&
    isString(value.title) &&
    isString(value.detail) &&
    isNumber(value.durationMinutes)
  );
}

function isDeadline(value: unknown): value is Deadline {
  return (
    isRecord(value) &&
    (value.kind === "BOSS" || value.kind === "Prazo") &&
    isString(value.title) &&
    isString(value.subject) &&
    isString(value.date)
  );
}

function isReview(value: unknown): value is Review {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.subject) &&
    isString(value.topic) &&
    isString(value.dueDate)
  );
}

function isTask(value: unknown): value is Task {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isString(value.category) &&
    isBoolean(value.completed)
  );
}

function isAgendaItem(value: unknown): value is AgendaItem {
  return (
    isRecord(value) &&
    isString(value.time) &&
    isTask(value)
  );
}

function isReading(value: unknown): value is Reading {
  return (
    isRecord(value) &&
    isString(value.title) &&
    isString(value.author) &&
    isNumber(value.currentPage) &&
    isNumber(value.totalPages) &&
    isNumber(value.dailyTarget)
  );
}

function isHabit(value: unknown): value is Habit {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isBoolean(value.completed)
  );
}

function isActivityDay(value: unknown): value is ActivityDay {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isNumber(value.minutes)
  );
}

export function isTodayDashboard(value: unknown): value is TodayDashboard {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isWeeklyGoal(value.weeklyQuestions) &&
    (value.focus === null || isFocusItem(value.focus)) &&
    (value.deadline === null || isDeadline(value.deadline)) &&
    isArrayOf(value.reviews, isReview) &&
    isArrayOf(value.priorities, isTask) &&
    isArrayOf(value.agenda, isAgendaItem) &&
    isArrayOf(value.tomorrow, isTask) &&
    (value.reading === null || isReading(value.reading)) &&
    isArrayOf(value.habits, isHabit) &&
    (value.physicalActivity === null || isString(value.physicalActivity)) &&
    isArrayOf(value.activity, isActivityDay)
  );
}
