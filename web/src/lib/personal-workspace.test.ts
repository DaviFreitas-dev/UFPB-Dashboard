import { describe, expect, it } from "vitest";

import { isPersonalWorkspace } from "./personal-workspace";

const workspace = {
  date: "2026-08-24",
  user: {
    level: 4,
    xp: 3420,
    xpInLevel: 420,
    xpPerLevel: 1000,
    xpToNextLevel: 580,
    streakDays: 6,
    longestStreak: 8,
  },
  tasks: {
    total: 2,
    completed: 1,
    items: [
      {
        id: "task-1",
        title: "Revisar funções",
        category: "Estudos",
        completed: true,
        mutable: true,
      },
    ],
  },
  habits: {
    total: 1,
    completed: 0,
    items: [
      {
        configId: "habit-config-1",
        logId: null,
        title: "Ler",
        completed: false,
        streakDays: 4,
      },
    ],
  },
  reading: {
    items: [
      {
        id: "book-1",
        title: "O homem que calculava",
        author: "Malba Tahan",
        currentPage: 84,
        totalPages: 240,
        dailyTarget: 20,
        remainingTarget: 20,
        status: "Lendo",
        progress: 0.35,
        mutable: true,
      },
    ],
  },
  activity: {
    items: [{ id: "activity-1", type: "Treino", completed: true }],
  },
};

describe("personal workspace contract", () => {
  it("aceita o contrato completo de rotina pessoal", () => {
    expect(isPersonalWorkspace(workspace)).toBe(true);
  });

  it("recusa uma resposta sem o id do log opcional de hábito", () => {
    expect(
      isPersonalWorkspace({
        ...workspace,
        habits: {
          ...workspace.habits,
          items: [{ ...workspace.habits.items[0], logId: undefined }],
        },
      }),
    ).toBe(false);
  });

  it("recusa uma tarefa sem indicação explícita de mutabilidade", () => {
    expect(
      isPersonalWorkspace({
        ...workspace,
        tasks: {
          ...workspace.tasks,
          items: [{ ...workspace.tasks.items[0], mutable: undefined }],
        },
      }),
    ).toBe(false);
  });

  it("recusa progresso de leitura que não seja numérico", () => {
    expect(
      isPersonalWorkspace({
        ...workspace,
        reading: {
          items: [{ ...workspace.reading.items[0], progress: "35%" }],
        },
      }),
    ).toBe(false);
  });

  it("recusa leitura sem mutabilidade explícita", () => {
    expect(isPersonalWorkspace({
      ...workspace,
      reading: { items: [{ ...workspace.reading.items[0], mutable: undefined }] },
    })).toBe(false);
  });
});
