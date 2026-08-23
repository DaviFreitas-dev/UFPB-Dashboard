import { createDemoRoutine } from "@/lib/demo-routine";
import { fetchNexoApi } from "@/lib/nexo-api";
import { isRoutineDashboard, type RoutineResult } from "@/lib/routine";

export async function loadRoutineDashboard(targetDate?: string): Promise<RoutineResult> {
  const path = targetDate
    ? `/v1/routine?date=${encodeURIComponent(targetDate)}`
    : "/v1/routine";
  const payload = await fetchNexoApi(path);

  if (payload === null) {
    return {
      routine: createDemoRoutine(
        targetDate ? new Date(`${targetDate}T12:00:00`) : undefined,
      ),
      source: "demo",
    };
  }

  if (!isRoutineDashboard(payload)) {
    throw new Error("A API do NEXO retornou uma rotina inválida.");
  }

  return {
    routine: payload,
    source: "api",
  };
}
