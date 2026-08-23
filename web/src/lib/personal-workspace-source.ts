import { createDemoPersonalWorkspace } from "@/lib/demo-personal-workspace";
import { fetchNexoApi } from "@/lib/nexo-api";
import {
  isPersonalWorkspace,
  type PersonalWorkspaceResult,
} from "@/lib/personal-workspace";

export async function loadPersonalWorkspace(
  targetDate?: string,
): Promise<PersonalWorkspaceResult> {
  const path = targetDate
    ? `/v1/personal?date=${encodeURIComponent(targetDate)}`
    : "/v1/personal";
  const payload = await fetchNexoApi(path);

  if (payload === null) {
    return {
      workspace: createDemoPersonalWorkspace(
        targetDate ? new Date(`${targetDate}T12:00:00`) : undefined,
      ),
      source: "demo",
    };
  }

  if (!isPersonalWorkspace(payload)) {
    throw new Error("A API do NEXO retornou dados pessoais inválidos.");
  }

  return { workspace: payload, source: "api" };
}
