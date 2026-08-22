import { isDashboardUser, type DashboardUser } from "@/lib/dashboard";

export type RoutineItem = {
  id: string;
  time: string;
  title: string;
  category: string;
  kind: "fixed" | "custom";
  completed: boolean;
};

export type RoutineDashboard = {
  date: string;
  user: DashboardUser;
  total: number;
  completed: number;
  fixedCount: number;
  customCount: number;
  items: RoutineItem[];
};

export type RoutineResult = {
  routine: RoutineDashboard;
  source: "api" | "demo";
};

function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const parsed = new Date(year, month - 1, day, 12);

  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }
  return parsed;
}

export function normalizeRoutineDate(value: string | undefined, fallback = new Date()): string {
  if (value && parseIsoDate(value)) {
    return value;
  }
  return isoDate(fallback);
}

export function addRoutineDays(value: string, amount: number): string {
  const date = parseIsoDate(value);
  if (!date) return value;
  date.setDate(date.getDate() + amount);
  return isoDate(date);
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

function isRoutineItem(value: unknown): value is RoutineItem {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.time) &&
    isString(value.title) &&
    isString(value.category) &&
    (value.kind === "fixed" || value.kind === "custom") &&
    isBoolean(value.completed)
  );
}

export function isRoutineDashboard(value: unknown): value is RoutineDashboard {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isNumber(value.total) &&
    isNumber(value.completed) &&
    isNumber(value.fixedCount) &&
    isNumber(value.customCount) &&
    Array.isArray(value.items) &&
    value.items.every(isRoutineItem)
  );
}
