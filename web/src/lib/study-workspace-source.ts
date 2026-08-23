import { createDemoStudyWorkspace } from "@/lib/demo-study-workspace";
import { fetchNexoApi } from "@/lib/nexo-api";
import { isStudyWorkspace, type StudyWorkspaceResult } from "@/lib/study-workspace";

export async function loadStudyWorkspace(): Promise<StudyWorkspaceResult> {
  const payload = await fetchNexoApi("/v1/studies");

  if (payload === null) {
    return { studies: createDemoStudyWorkspace(), source: "demo" };
  }

  if (!isStudyWorkspace(payload)) {
    throw new Error("A API do NEXO retornou um espaço de estudos inválido.");
  }

  return { studies: payload, source: "api" };
}
