import type { StudyWorkspace } from "@/lib/study-workspace";

function dateText(reference: Date): string {
  const year = reference.getFullYear();
  const month = String(reference.getMonth() + 1).padStart(2, "0");
  const day = String(reference.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createDemoStudyWorkspace(reference = new Date()): StudyWorkspace {
  const date = dateText(reference);

  return {
    date,
    user: {
      level: 4,
      xp: 3420,
      xpInLevel: 420,
      xpPerLevel: 1000,
      xpToNextLevel: 580,
      streakDays: 6,
      longestStreak: 8,
    },
    cycle: {
      totalHours: 30,
      remainingHours: 16,
      completedHours: 14,
      progress: 14 / 30,
      subjects: [
        { id: "matematica", subject: "Matemática", environment: "Mesa", plannedHours: 8, remainingHours: 4, completedHours: 4, progress: 0.5, legacy: false },
        { id: "fisica", subject: "Física", environment: "Mesa", plannedHours: 6, remainingHours: 4, completedHours: 2, progress: 1 / 3, legacy: false },
        { id: "redacao", subject: "Redação", environment: "Ambos", plannedHours: 5, remainingHours: 2, completedHours: 3, progress: 0.6, legacy: false },
        { id: "biologia", subject: "Biologia", environment: "Transporte", plannedHours: 5, remainingHours: 3, completedHours: 2, progress: 0.4, legacy: false },
        { id: "historia", subject: "História", environment: "Transporte", plannedHours: 3, remainingHours: 2, completedHours: 1, progress: 1 / 3, legacy: false },
        { id: "filosofia", subject: "Filosofia", environment: "Ambos", plannedHours: 3, remainingHours: 1, completedHours: 2, progress: 2 / 3, legacy: true },
      ],
    },
    missions: {
      durationOptions: [1, 2, 3, 4, 5, 6],
      totalAvailableHours: 16,
      subjects: [
        { id: "matematica", subject: "Matemática", environment: "Mesa", remainingHours: 4 },
        { id: "fisica", subject: "Física", environment: "Mesa", remainingHours: 4 },
        { id: "redacao", subject: "Redação", environment: "Ambos", remainingHours: 2 },
        { id: "biologia", subject: "Biologia", environment: "Transporte", remainingHours: 3 },
        { id: "historia", subject: "História", environment: "Transporte", remainingHours: 2 },
        { id: "filosofia", subject: "Filosofia", environment: "Ambos", remainingHours: 1 },
      ],
    },
    progress: {
      totals: { studyHours: 86, questions: 1240, correct: 964, wrong: 276, accuracy: 0.7774, streakDays: 6 },
      week: { start: "2026-08-17", end: "2026-08-23", studyHours: 14, questions: 220, accuracy: 0.8, tasksCompleted: 7, reviewsCompleted: 3 },
      studyHistory: [
        { date: "2026-08-16", hours: 2 }, { date: "2026-08-17", hours: 3 }, { date: "2026-08-18", hours: 1 }, { date: "2026-08-19", hours: 2 }, { date: "2026-08-20", hours: 2 }, { date: "2026-08-21", hours: 2 }, { date, hours: 2 },
      ],
      weeklyAccuracy: [
        { weekStart: "2026-07-06", questions: 104, accuracy: 0.68 }, { weekStart: "2026-07-13", questions: 146, accuracy: 0.71 }, { weekStart: "2026-07-20", questions: 128, accuracy: 0.73 }, { weekStart: "2026-07-27", questions: 162, accuracy: 0.75 }, { weekStart: "2026-08-03", questions: 176, accuracy: 0.78 }, { weekStart: "2026-08-10", questions: 184, accuracy: 0.76 }, { weekStart: "2026-08-17", questions: 220, accuracy: 0.8 },
      ],
      subjects: [
        { subject: "Matemática", questions: 350, correct: 277, wrong: 73, accuracy: 0.7914, studyHours: 25 },
        { subject: "Física", questions: 260, correct: 191, wrong: 69, accuracy: 0.7346, studyHours: 18 },
        { subject: "Biologia", questions: 210, correct: 175, wrong: 35, accuracy: 0.8333, studyHours: 14 },
        { subject: "História", questions: 190, correct: 154, wrong: 36, accuracy: 0.8105, studyHours: 12 },
        { subject: "Redação", questions: 230, correct: 167, wrong: 63, accuracy: 0.7261, studyHours: 17 },
      ],
      reviewPoints: [
        { subject: "Física", topic: "Cinemática", quantity: 8 }, { subject: "Redação", topic: "Argumentação", quantity: 6 }, { subject: "Matemática", topic: "Funções", quantity: 5 },
      ],
    },
  };
}
