import { isDashboardUser, type DashboardUser } from "@/lib/dashboard";

export type PersonalTask = {
  id: string;
  title: string;
  category: string;
  completed: boolean;
  mutable: boolean;
};

export type PersonalHabit = {
  configId: string;
  logId: string | null;
  title: string;
  completed: boolean;
  streakDays: number;
};

export type PersonalReading = {
  id: string;
  title: string;
  author: string;
  currentPage: number;
  totalPages: number;
  dailyTarget: number;
  remainingTarget: number;
  status: string;
  progress: number;
};

export type PersonalActivity = {
  id: string;
  type: string;
  completed: boolean;
};

type PersonalCollection<T> = {
  total: number;
  completed: number;
  items: T[];
};

export type PersonalWorkspace = {
  date: string;
  user: DashboardUser;
  tasks: PersonalCollection<PersonalTask>;
  habits: PersonalCollection<PersonalHabit>;
  reading: { items: PersonalReading[] };
  activity: { items: PersonalActivity[] };
};

export type PersonalWorkspaceResult = {
  workspace: PersonalWorkspace;
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

function isPersonalTask(value: unknown): value is PersonalTask {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isString(value.category) &&
    isBoolean(value.completed) &&
    isBoolean(value.mutable)
  );
}

function isPersonalHabit(value: unknown): value is PersonalHabit {
  return (
    isRecord(value) &&
    isString(value.configId) &&
    (value.logId === null || isString(value.logId)) &&
    isString(value.title) &&
    isBoolean(value.completed) &&
    isNumber(value.streakDays)
  );
}

function isPersonalReading(value: unknown): value is PersonalReading {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isString(value.author) &&
    isNumber(value.currentPage) &&
    isNumber(value.totalPages) &&
    isNumber(value.dailyTarget) &&
    isNumber(value.remainingTarget) &&
    isString(value.status) &&
    isNumber(value.progress)
  );
}

function isPersonalActivity(value: unknown): value is PersonalActivity {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.type) &&
    isBoolean(value.completed)
  );
}

function isCollection<T>(
  value: unknown,
  itemGuard: (item: unknown) => item is T,
): value is PersonalCollection<T> {
  return (
    isRecord(value) &&
    isNumber(value.total) &&
    isNumber(value.completed) &&
    Array.isArray(value.items) &&
    value.items.every(itemGuard)
  );
}

export function isPersonalWorkspace(value: unknown): value is PersonalWorkspace {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isCollection(value.tasks, isPersonalTask) &&
    isCollection(value.habits, isPersonalHabit) &&
    isRecord(value.reading) &&
    Array.isArray(value.reading.items) &&
    value.reading.items.every(isPersonalReading) &&
    isRecord(value.activity) &&
    Array.isArray(value.activity.items) &&
    value.activity.items.every(isPersonalActivity)
  );
}
