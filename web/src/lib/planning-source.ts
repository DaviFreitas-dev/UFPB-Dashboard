import { createDemoPlanning } from "@/lib/demo-planning";
import { fetchNexoApi } from "@/lib/nexo-api";
import { isPlanningDashboard, type PlanningResult } from "@/lib/planning";

export async function loadPlanningDashboard(): Promise<PlanningResult> {
  const payload = await fetchNexoApi("/v1/planning");

  if (payload === null) {
    return {
      planning: createDemoPlanning(),
      source: "demo",
    };
  }

  if (!isPlanningDashboard(payload)) {
    throw new Error("A API do NEXO retornou um planejamento inválido.");
  }

  return {
    planning: payload,
    source: "api",
  };
}
