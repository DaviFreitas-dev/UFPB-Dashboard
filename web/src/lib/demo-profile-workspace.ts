import type { ProfileWorkspace } from "@/lib/profile-workspace";

function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createDemoProfileWorkspace(reference = new Date()): ProfileWorkspace {
  return {
    date: isoDate(reference),
    user: {
      level: 4,
      xp: 3420,
      xpInLevel: 420,
      xpPerLevel: 1000,
      xpToNextLevel: 580,
      streakDays: 6,
      longestStreak: 12,
    },
    achievements: {
      unlocked: 4,
      total: 11,
      items: [
        { id: "1", title: "Primeiro passo", description: "Conclua sua primeira hora de estudo.", unlocked: true, unlockedAt: "2026-07-04" },
        { id: "2", title: "10 horas", description: "Acumule 10 horas de estudo.", unlocked: true, unlockedAt: "2026-07-11" },
        { id: "3", title: "50 horas", description: "Acumule 50 horas de estudo.", unlocked: false, unlockedAt: null },
        { id: "4", title: "100 questões", description: "Resolva 100 questões.", unlocked: true, unlockedAt: "2026-08-08" },
        { id: "5", title: "500 questões", description: "Resolva 500 questões.", unlocked: false, unlockedAt: null },
        { id: "6", title: "1.000 questões", description: "Resolva 1.000 questões.", unlocked: false, unlockedAt: null },
        { id: "7", title: "Precisão", description: "Mantenha 80% de acerto em pelo menos 100 questões.", unlocked: true, unlockedAt: "2026-08-15" },
        { id: "8", title: "Uma semana", description: "Mantenha uma sequência geral de 7 dias.", unlocked: false, unlockedAt: null },
        { id: "9", title: "Revisor", description: "Conclua 10 revisões programadas.", unlocked: false, unlockedAt: null },
        { id: "10", title: "Boss derrotado", description: "Conclua uma prova cadastrada.", unlocked: false, unlockedAt: null },
        { id: "11", title: "Nível alto", description: "Alcance 5.000 XP.", unlocked: false, unlockedAt: null },
      ],
    },
    settings: {
      environments: ["Mesa", "Transporte", "Ambos"],
      subjects: [
        { discipline: "Matemática", hours: 5, environment: "Mesa" },
        { discipline: "Linguagens", hours: 4, environment: "Transporte" },
        { discipline: "Física", hours: 3, environment: "Mesa" },
        { discipline: "Redação", hours: 3, environment: "Ambos" },
      ],
      cycle: [
        { discipline: "Matemática", remainingHours: 3 },
        { discipline: "Linguagens", remainingHours: 4 },
        { discipline: "Física", remainingHours: 2 },
        { discipline: "Redação", remainingHours: 3 },
      ],
    },
  };
}
