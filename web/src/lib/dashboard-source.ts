import {
  type DashboardResult,
  isTodayDashboard,
} from "@/lib/dashboard";
import { createDemoDashboard } from "@/lib/demo-dashboard";
import { fetchNexoApi } from "@/lib/nexo-api";

export async function loadTodayDashboard(): Promise<DashboardResult> {
  const payload = await fetchNexoApi("/v1/dashboard/today");

  if (payload === null) {
    return {
      dashboard: createDemoDashboard(),
      source: "demo",
    };
  }

  if (!isTodayDashboard(payload)) {
    throw new Error("A API do NEXO retornou um painel inválido.");
  }

  return {
    dashboard: payload,
    source: "api",
  };
}
