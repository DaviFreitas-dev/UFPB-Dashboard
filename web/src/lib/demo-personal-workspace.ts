import { createDemoDashboard } from "@/lib/demo-dashboard";
import type { PersonalWorkspace } from "@/lib/personal-workspace";

function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createDemoPersonalWorkspace(reference = new Date()): PersonalWorkspace {
  const tasks = [
    { id: "task-1", title: "Revisar funções", category: "Estudos", completed: true, mutable: false },
    { id: "task-2", title: "Separar material", category: "Escola", completed: false, mutable: false },
    { id: "task-3", title: "Organizar a semana", category: "Pessoal", completed: false, mutable: false },
  ];
  const habits = [
    {
      configId: "habit-config-1",
      logId: "habit-log-1",
      title: "Ler 20 páginas",
      completed: true,
      streakDays: 6,
    },
    {
      configId: "habit-config-2",
      logId: null,
      title: "Alongar",
      completed: false,
      streakDays: 3,
    },
    {
      configId: "habit-config-3",
      logId: "habit-log-3",
      title: "Revisar o dia",
      completed: true,
      streakDays: 9,
    },
  ];

  return {
    date: isoDate(reference),
    user: createDemoDashboard(reference).user,
    tasks: {
      total: tasks.length,
      completed: tasks.filter((item) => item.completed).length,
      items: tasks,
    },
    habits: {
      total: habits.length,
      completed: habits.filter((item) => item.completed).length,
      items: habits,
    },
    reading: {
      items: [
        {
          id: "book-1",
          mutable: false,
          title: "O homem que calculava",
          author: "Malba Tahan",
          currentPage: 84,
          totalPages: 240,
          dailyTarget: 20,
          remainingTarget: 20,
          status: "Lendo",
          progress: 0.35,
        },
        {
          id: "book-2",
          mutable: false,
          title: "Capitães da Areia",
          author: "Jorge Amado",
          currentPage: 182,
          totalPages: 182,
          dailyTarget: 15,
          remainingTarget: 0,
          status: "Concluído",
          progress: 1,
        },
      ],
    },
    activity: {
      items: [
        { id: "activity-1", type: "Treino", completed: true },
        { id: "activity-2", type: "Caminhada", completed: true },
      ],
    },
  };
}
