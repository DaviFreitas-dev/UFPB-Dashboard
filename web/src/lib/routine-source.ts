import { createDemoRoutine } from "@/lib/demo-routine";
import { fetchNexoApi } from "@/lib/nexo-api";
import { isRoutineDashboard, type RoutineResult } from "@/lib/routine";

export async function loadRoutineDashboard(targetDate: string): Promise<RoutineResult> {
  const payload = await fetchNexoApi(
    `/v1/routine?date=${encodeURIComponent(targetDate)}`,
  );

  if (payload === null) {
    return {
      routine: createDemoRoutine(new Date(`${targetDate}T12:00:00`)),
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
