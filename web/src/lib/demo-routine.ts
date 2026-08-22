import { createDemoDashboard } from "@/lib/demo-dashboard";
import type { RoutineDashboard } from "@/lib/routine";

function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createDemoRoutine(reference = new Date()): RoutineDashboard {
  const user = createDemoDashboard(reference).user;
  const items = [
    {
      id: "fixed-1",
      time: "08:00",
      title: "Aula de Física",
      category: "Escola",
      kind: "fixed" as const,
      completed: true,
    },
    {
      id: "custom-1",
      time: "11:30",
      title: "Resolver pendência no banco",
      category: "Avulso",
      kind: "custom" as const,
      completed: true,
    },
    {
      id: "fixed-2",
      time: "14:00",
      title: "Estudo dirigido",
      category: "Estudo",
      kind: "fixed" as const,
      completed: false,
    },
    {
      id: "custom-2",
      time: "17:00",
      title: "Consulta",
      category: "Avulso",
      kind: "custom" as const,
      completed: false,
    },
    {
      id: "fixed-3",
      time: "18:30",
      title: "Academia",
      category: "Saúde",
      kind: "fixed" as const,
      completed: false,
    },
  ];

  return {
    date: isoDate(reference),
    user,
    total: items.length,
    completed: items.filter((item) => item.completed).length,
    fixedCount: items.filter((item) => item.kind === "fixed").length,
    customCount: items.filter((item) => item.kind === "custom").length,
    items,
  };
}
