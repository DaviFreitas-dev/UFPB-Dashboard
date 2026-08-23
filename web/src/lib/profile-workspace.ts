import {
  formatDatePtBr,
  isDashboardUser,
  type DashboardUser,
} from "@/lib/dashboard";

export type Achievement = {
  id: string;
  title: string;
  description: string;
  unlocked: boolean;
  unlockedAt: string | null;
};

export type ProfileWorkspace = {
  date: string;
  user: DashboardUser;
  achievements: {
    unlocked: number;
    total: number;
    items: Achievement[];
  };
  settings: {
    environments: string[];
    subjects: Array<{
      discipline: string;
      hours: number;
      environment: string;
    }>;
    cycle: Array<{
      discipline: string;
      remainingHours: number;
    }>;
  };
};

export type ProfileWorkspaceResult = {
  workspace: ProfileWorkspace;
  source: "api" | "demo";
};

export function achievementFootnote(achievement: Achievement): string {
  if (achievement.unlockedAt) {
    return `Liberada em ${formatDatePtBr(achievement.unlockedAt)}`;
  }
  return achievement.unlocked
    ? "Concluída recentemente."
    : "Requisito ainda não atingido.";
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

function isAchievement(value: unknown): value is Achievement {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.title) &&
    isString(value.description) &&
    isBoolean(value.unlocked) &&
    (value.unlockedAt === null || isString(value.unlockedAt))
  );
}

function isSubject(value: unknown): value is ProfileWorkspace["settings"]["subjects"][number] {
  return (
    isRecord(value) &&
    isString(value.discipline) &&
    isNumber(value.hours) &&
    isString(value.environment)
  );
}

function isCycleItem(value: unknown): value is ProfileWorkspace["settings"]["cycle"][number] {
  return (
    isRecord(value) &&
    isString(value.discipline) &&
    isNumber(value.remainingHours)
  );
}

export function isProfileWorkspace(value: unknown): value is ProfileWorkspace {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isRecord(value.achievements) &&
    isNumber(value.achievements.unlocked) &&
    isNumber(value.achievements.total) &&
    Array.isArray(value.achievements.items) &&
    value.achievements.items.every(isAchievement) &&
    isRecord(value.settings) &&
    Array.isArray(value.settings.environments) &&
    value.settings.environments.every(isString) &&
    Array.isArray(value.settings.subjects) &&
    value.settings.subjects.every(isSubject) &&
    Array.isArray(value.settings.cycle) &&
    value.settings.cycle.every(isCycleItem)
  );
}
