import type { ActivityDay, TodayDashboard } from "@/lib/dashboard";

function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, amount: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
}

function activityFor(reference: Date): ActivityDay[] {
  const minutes = [0, 95, 40, 120, 70, 155, 35];

  return minutes.map((value, index) => ({
    date: isoDate(addDays(reference, index - 6)),
    minutes: value,
  }));
}

export function createDemoDashboard(reference = new Date()): TodayDashboard {
  const today = isoDate(reference);

  return {
    date: today,
    user: {
      level: 4,
      xp: 3_420,
      nextLevelXp: 4_000,
      streakDays: 6,
      longestStreak: 14,
    },
    weeklyQuestions: {
      completed: 126,
      target: 200,
      previousWeek: 98,
    },
    focus: {
      eyebrow: "Próximo passo",
      title: "Revisar funções e resolver 20 questões",
      detail: "Matemática · revisão pendente",
      durationMinutes: 50,
    },
    deadline: {
      kind: "BOSS",
      title: "Simulado de Física",
      subject: "Física",
      date: isoDate(addDays(reference, 5)),
    },
    reviews: [
      {
        id: "review-1",
        subject: "Matemática",
        topic: "Funções",
        dueDate: today,
      },
      {
        id: "review-2",
        subject: "Química",
        topic: "Estequiometria",
        dueDate: today,
      },
    ],
    priorities: [
      {
        id: "task-1",
        title: "Resolver 30 questões",
        category: "Estudos",
        completed: false,
      },
      {
        id: "task-2",
        title: "Enviar trabalho de História",
        category: "Escola",
        completed: true,
      },
    ],
    agenda: [
      {
        id: "agenda-1",
        time: "14:00",
        title: "Estudo dirigido",
        category: "Estudos",
        completed: false,
      },
      {
        id: "agenda-2",
        time: "18:30",
        title: "Academia",
        category: "Atividade",
        completed: false,
      },
    ],
    tomorrow: [
      {
        id: "tomorrow-1",
        title: "Terminar a lista de Física",
        category: "Estudos",
        completed: false,
      },
      {
        id: "tomorrow-2",
        title: "Revisar redação",
        category: "Escola",
        completed: false,
      },
    ],
    reading: {
      title: "O homem que calculava",
      author: "Malba Tahan",
      currentPage: 84,
      totalPages: 240,
      dailyTarget: 20,
    },
    habits: [
      { id: "habit-1", title: "Ler 20 páginas", completed: true },
      { id: "habit-2", title: "Revisar o dia", completed: false },
      { id: "habit-3", title: "Alongar", completed: true },
    ],
    physicalActivity: "Treino de força",
    activity: activityFor(reference),
  };
}
