import {
  type DashboardResult,
  isTodayDashboard,
} from "@/lib/dashboard";
import { createDemoDashboard } from "@/lib/demo-dashboard";

export async function loadTodayDashboard(): Promise<DashboardResult> {
  const baseUrl = process.env.NEXO_API_URL?.replace(/\/$/, "");

  if (!baseUrl) {
    return {
      dashboard: createDemoDashboard(),
      source: "demo",
    };
  }

  const response = await fetch(`${baseUrl}/v1/dashboard/today`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`A API do NEXO respondeu com status ${response.status}.`);
  }

  const payload: unknown = await response.json();
  if (!isTodayDashboard(payload)) {
    throw new Error("A API do NEXO retornou um painel inválido.");
  }

  return {
    dashboard: payload,
    source: "api",
  };
}
