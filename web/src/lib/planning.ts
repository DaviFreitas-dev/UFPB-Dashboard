import { isDashboardUser, type DashboardUser, type Review, type Task } from "@/lib/dashboard";

export type PlanningSummary = {
  start: string;
  end: string;
  studyHours: number;
  questions: number;
  accuracy: number;
  tasksCompleted: number;
  reviewsCompleted: number;
};

export type PlanningAgendaItem = {
  id: string;
  time: string;
  title: string;
  category: string;
};

export type PlanningDay = {
  name: string;
  date: string;
  isToday: boolean;
  items: PlanningAgendaItem[];
};

export type PlanningAssessment = {
  id: string;
  title: string;
  kind: string;
  subject: string;
  date: string;
  questionGoal: number;
  isBoss: boolean;
};

export type WeakPoint = {
  id: string;
  subject: string;
  topic: string;
  quantity: number;
  note: string;
};

export type JournalEntry = {
  id: string;
  date: string;
  text: string;
};

export type PlanningDashboard = {
  date: string;
  user: DashboardUser;
  summary: PlanningSummary;
  weeklyQuestions: {
    completed: number;
    target: number;
    previousWeek: number;
  };
  week: PlanningDay[];
  assessments: PlanningAssessment[];
  reviews: Review[];
  weakPoints: WeakPoint[];
  tomorrow: Task[];
  journal: JournalEntry[];
};

export type PlanningResult = {
  planning: PlanningDashboard;
  source: "api" | "demo";
};

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

function isArrayOf<T>(value: unknown, guard: (item: unknown) => item is T): value is T[] {
  return Array.isArray(value) && value.every(guard);
}

function isSummary(value: unknown): value is PlanningSummary {
  return (
    isRecord(value) &&
    isString(value.start) &&
    isString(value.end) &&
    isNumber(value.studyHours) &&
    isNumber(value.questions) &&
    isNumber(value.accuracy) &&
    isNumber(value.tasksCompleted) &&
    isNumber(value.reviewsCompleted)
  );
}

function isWeeklyQuestions(value: unknown): value is PlanningDashboard["weeklyQuestions"] {
  return (
    isRecord(value) &&
    isNumber(value.completed) &&
    isNumber(value.target) &&
    isNumber(value.previousWeek)
  );
}

function isAgendaItem(value: unknown): value is PlanningAgendaItem {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.time) &&
    isString(value.title) &&
    isString(value.category)
  );
}

function isPlanningDay(value: unknown): value is PlanningDay {
  return (
    isRecord(value) &&
    isString(value.name) &&
    isString(value.date) &&
    isBoolean(value.isToday) &&
    isArrayOf(value.items, isAgendaItem)
  );
}

function isAssessment(value: unknown): value is PlanningAssessment {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isString(value.kind) &&
    isString(value.subject) &&
    isString(value.date) &&
    isNumber(value.questionGoal) &&
    isBoolean(value.isBoss)
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

function isWeakPoint(value: unknown): value is WeakPoint {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.subject) &&
    isString(value.topic) &&
    isNumber(value.quantity) &&
    isString(value.note)
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

function isJournalEntry(value: unknown): value is JournalEntry {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.date) &&
    isString(value.text)
  );
}

export function isPlanningDashboard(value: unknown): value is PlanningDashboard {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isSummary(value.summary) &&
    isWeeklyQuestions(value.weeklyQuestions) &&
    isArrayOf(value.week, isPlanningDay) &&
    isArrayOf(value.assessments, isAssessment) &&
    isArrayOf(value.reviews, isReview) &&
    isArrayOf(value.weakPoints, isWeakPoint) &&
    isArrayOf(value.tomorrow, isTask) &&
    isArrayOf(value.journal, isJournalEntry)
  );
}
