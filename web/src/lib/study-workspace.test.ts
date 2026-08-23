import { describe, expect, it } from "vitest";

import {
  drawLocalMission,
  isStudyWorkspace,
  type StudyWorkspace,
} from "./study-workspace";

const workspace: StudyWorkspace = {
  date: "2026-08-22",
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
    totalHours: 24,
    remainingHours: 15,
    completedHours: 9,
    progress: 0.375,
    subjects: [
      {
        id: "math",
        subject: "Matemática",
        environment: "Mesa",
        plannedHours: 8,
        remainingHours: 5,
        completedHours: 3,
        progress: 0.375,
        legacy: false,
      },
      {
        id: "bio",
        subject: "Biologia",
        environment: "Ambos",
        plannedHours: 4,
        remainingHours: 2,
        completedHours: 2,
        progress: 0.5,
        legacy: false,
      },
    ],
  },
  missions: {
    durationOptions: [1, 2, 3],
    totalAvailableHours: 7,
    subjects: [
      { id: "math", subject: "Matemática", environment: "Mesa", remainingHours: 5 },
      { id: "bio", subject: "Biologia", environment: "Ambos", remainingHours: 2 },
    ],
  },
  progress: {
    totals: {
      studyHours: 42,
      questions: 320,
      correct: 256,
      wrong: 64,
      accuracy: 0.8,
      streakDays: 6,
    },
    week: {
      start: "2026-08-17",
      end: "2026-08-23",
      studyHours: 11,
      questions: 80,
      accuracy: 0.75,
      tasksCompleted: 4,
      reviewsCompleted: 2,
    },
    studyHistory: [{ date: "2026-08-22", hours: 2 }],
    weeklyAccuracy: [{ weekStart: "2026-08-17", questions: 80, accuracy: 0.75 }],
    subjects: [
      {
        subject: "Matemática",
        questions: 80,
        correct: 60,
        wrong: 20,
        accuracy: 0.75,
        studyHours: 8,
      },
    ],
    reviewPoints: [{ subject: "Matemática", topic: "Funções", quantity: 3 }],
  },
};

describe("study workspace contract", () => {
  it("aceita o contrato completo de estudos", () => {
    expect(isStudyWorkspace(workspace)).toBe(true);
  });

  it("rejeita uma resposta sem o saldo da missão", () => {
    const missingAvailability = {
      ...workspace,
      missions: { ...workspace.missions, totalAvailableHours: undefined },
    };

    expect(isStudyWorkspace(missingAvailability)).toBe(false);
  });
});

describe("drawLocalMission", () => {
  it("respeita o ambiente e nunca ultrapassa o saldo disponível", () => {
    const mission = drawLocalMission(workspace.missions.subjects, "Mesa", 6, () => 0);

    expect(mission).toEqual([
      { id: "math", subject: "Matemática", hours: 5 },
      { id: "bio", subject: "Biologia", hours: 1 },
    ]);
  });

  it("retorna uma missão parcial quando faltam horas para a duração escolhida", () => {
    const mission = drawLocalMission(workspace.missions.subjects, "Transporte", 4, () => 0);

    expect(mission).toEqual([{ id: "bio", subject: "Biologia", hours: 2 }]);
  });

  it("ignora saldos fracionários que não completam uma hora", () => {
    const mission = drawLocalMission(
      [{ id: "legacy", subject: "Legado", environment: "Ambos", remainingHours: 0.5 }],
      "Ambos",
      1,
      () => 0,
    );

    expect(mission).toEqual([]);
  });
});
