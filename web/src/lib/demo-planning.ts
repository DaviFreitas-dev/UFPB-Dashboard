import { createDemoDashboard } from "@/lib/demo-dashboard";
import type { PlanningDashboard } from "@/lib/planning";

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

export function createDemoPlanning(reference = new Date()): PlanningDashboard {
  const dashboard = createDemoDashboard(reference);
  const weekday = reference.getDay();
  const monday = addDays(reference, weekday === 0 ? -6 : 1 - weekday);
  const weekdays = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
  const agenda = [
    [{ id: "w1", time: "08:00", title: "Aula de Física", category: "Escola" }],
    [{ id: "w2", time: "14:00", title: "Lista de Matemática", category: "Estudo" }],
    [{ id: "w3", time: "18:30", title: "Academia", category: "Saúde" }],
    [{ id: "w4", time: "15:00", title: "Redação", category: "Estudo" }],
    [{ id: "w5", time: "10:00", title: "Revisão geral", category: "Estudo" }],
    [{ id: "w6", time: "09:00", title: "Simulado", category: "Escola" }],
    [],
  ];

  return {
    date: isoDate(reference),
    user: dashboard.user,
    summary: {
      start: isoDate(monday),
      end: isoDate(addDays(monday, 6)),
      studyHours: 8.5,
      questions: 126,
      accuracy: 0.79,
      tasksCompleted: 7,
      reviewsCompleted: 4,
    },
    weeklyQuestions: dashboard.weeklyQuestions,
    week: weekdays.map((name, index) => ({
      name,
      date: isoDate(addDays(monday, index)),
      isToday: isoDate(addDays(monday, index)) === isoDate(reference),
      items: agenda[index],
    })),
    assessments: [
      {
        id: "assessment-1",
        title: "Simulado de Física",
        kind: "Prova",
        subject: "Física",
        date: isoDate(addDays(reference, 5)),
        questionGoal: 50,
        isBoss: true,
      },
      {
        id: "assessment-2",
        title: "Trabalho de História",
        kind: "Trabalho",
        subject: "História",
        date: isoDate(addDays(reference, 9)),
        questionGoal: 0,
        isBoss: false,
      },
    ],
    reviews: dashboard.reviews,
    weakPoints: [
      {
        id: "error-1",
        subject: "Química",
        topic: "Estequiometria",
        quantity: 4,
        note: "Rever proporções e unidade molar.",
      },
      {
        id: "error-2",
        subject: "Matemática",
        topic: "Função composta",
        quantity: 2,
        note: "",
      },
    ],
    tomorrow: dashboard.tomorrow,
    journal: [
      {
        id: "journal-1",
        date: isoDate(reference),
        text: "Funções ficaram mais claras depois da lista de exercícios.",
      },
    ],
  };
}
