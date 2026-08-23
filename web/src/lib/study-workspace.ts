import { isDashboardUser, type DashboardUser } from "@/lib/dashboard";

export type StudySubject = {
  id: string;
  subject: string;
  environment: string;
  plannedHours: number;
  remainingHours: number;
  completedHours: number;
  progress: number;
  legacy: boolean;
};

export type MissionAvailability = {
  id: string;
  subject: string;
  environment: string;
  remainingHours: number;
};

export type LocalMissionItem = {
  id: string;
  subject: string;
  hours: number;
};

export type StudyWorkspace = {
  date: string;
  user: DashboardUser;
  cycle: {
    totalHours: number;
    remainingHours: number;
    completedHours: number;
    progress: number;
    subjects: StudySubject[];
  };
  missions: {
    durationOptions: number[];
    totalAvailableHours: number;
    subjects: MissionAvailability[];
  };
  progress: {
    totals: {
      studyHours: number;
      questions: number;
      correct: number;
      wrong: number;
      accuracy: number;
      streakDays: number;
    };
    week: {
      start: string;
      end: string;
      studyHours: number;
      questions: number;
      accuracy: number;
      tasksCompleted: number;
      reviewsCompleted: number;
    };
    studyHistory: Array<{ date: string; hours: number }>;
    weeklyAccuracy: Array<{ weekStart: string; questions: number; accuracy: number }>;
    subjects: Array<{
      subject: string;
      questions: number;
      correct: number;
      wrong: number;
      accuracy: number;
      studyHours: number;
    }>;
    reviewPoints: Array<{ subject: string; topic: string; quantity: number }>;
  };
};

export type StudyWorkspaceResult = {
  studies: StudyWorkspace;
  source: "api" | "demo";
};

export type MissionEnvironment = "Ambos" | "Mesa" | "Transporte";

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

function isStudySubject(value: unknown): value is StudySubject {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.subject) &&
    isString(value.environment) &&
    isNumber(value.plannedHours) &&
    isNumber(value.remainingHours) &&
    isNumber(value.completedHours) &&
    isNumber(value.progress) &&
    isBoolean(value.legacy)
  );
}

function isMissionAvailability(value: unknown): value is MissionAvailability {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.subject) &&
    isString(value.environment) &&
    isNumber(value.remainingHours)
  );
}

function isStudyHistoryPoint(
  value: unknown,
): value is StudyWorkspace["progress"]["studyHistory"][number] {
  return isRecord(value) && isString(value.date) && isNumber(value.hours);
}

function isWeeklyAccuracyPoint(
  value: unknown,
): value is StudyWorkspace["progress"]["weeklyAccuracy"][number] {
  return (
    isRecord(value) &&
    isString(value.weekStart) &&
    isNumber(value.questions) &&
    isNumber(value.accuracy)
  );
}

function isSubjectProgress(
  value: unknown,
): value is StudyWorkspace["progress"]["subjects"][number] {
  return (
    isRecord(value) &&
    isString(value.subject) &&
    isNumber(value.questions) &&
    isNumber(value.correct) &&
    isNumber(value.wrong) &&
    isNumber(value.accuracy) &&
    isNumber(value.studyHours)
  );
}

function isReviewPoint(
  value: unknown,
): value is StudyWorkspace["progress"]["reviewPoints"][number] {
  return (
    isRecord(value) &&
    isString(value.subject) &&
    isString(value.topic) &&
    isNumber(value.quantity)
  );
}

function isProgress(value: unknown): value is StudyWorkspace["progress"] {
  if (!isRecord(value) || !isRecord(value.totals) || !isRecord(value.week)) return false;

  const totals = value.totals;
  const week = value.week;
  return (
    isNumber(totals.studyHours) &&
    isNumber(totals.questions) &&
    isNumber(totals.correct) &&
    isNumber(totals.wrong) &&
    isNumber(totals.accuracy) &&
    isNumber(totals.streakDays) &&
    isString(week.start) &&
    isString(week.end) &&
    isNumber(week.studyHours) &&
    isNumber(week.questions) &&
    isNumber(week.accuracy) &&
    isNumber(week.tasksCompleted) &&
    isNumber(week.reviewsCompleted) &&
    isArrayOf(value.studyHistory, isStudyHistoryPoint) &&
    isArrayOf(value.weeklyAccuracy, isWeeklyAccuracyPoint) &&
    isArrayOf(value.subjects, isSubjectProgress) &&
    isArrayOf(value.reviewPoints, isReviewPoint)
  );
}

export function isStudyWorkspace(value: unknown): value is StudyWorkspace {
  return (
    isRecord(value) &&
    isString(value.date) &&
    isDashboardUser(value.user) &&
    isRecord(value.cycle) &&
    isNumber(value.cycle.totalHours) &&
    isNumber(value.cycle.remainingHours) &&
    isNumber(value.cycle.completedHours) &&
    isNumber(value.cycle.progress) &&
    isArrayOf(value.cycle.subjects, isStudySubject) &&
    isRecord(value.missions) &&
    isArrayOf(value.missions.durationOptions, isNumber) &&
    isNumber(value.missions.totalAvailableHours) &&
    isArrayOf(value.missions.subjects, isMissionAvailability) &&
    isProgress(value.progress)
  );
}

function supportsEnvironment(item: MissionAvailability, environment: MissionEnvironment): boolean {
  return environment === "Ambos" || item.environment === "Ambos" || item.environment === environment;
}

export function drawLocalMission(
  subjects: MissionAvailability[],
  environment: MissionEnvironment,
  duration: number,
  random: () => number = Math.random,
): LocalMissionItem[] {
  let remaining = Math.max(0, Math.floor(duration));
  const available = subjects
    .filter((item) => supportsEnvironment(item, environment))
    .map((item) => ({ ...item, remainingHours: Math.floor(item.remainingHours) }))
    .filter((item) => item.remainingHours > 0);
  const mission: LocalMissionItem[] = [];

  while (remaining > 0 && available.length) {
    const index = Math.min(available.length - 1, Math.max(0, Math.floor(random() * available.length)));
    const selected = available[index];
    const hours = Math.min(remaining, selected.remainingHours);
    mission.push({ id: selected.id, subject: selected.subject, hours });
    remaining -= hours;
    available.splice(index, 1);
  }

  return mission;
}
