import { createDemoProfileWorkspace } from "@/lib/demo-profile-workspace";
import { fetchNexoApi } from "@/lib/nexo-api";
import {
  isProfileWorkspace,
  type ProfileWorkspaceResult,
} from "@/lib/profile-workspace";

export async function loadProfileWorkspace(): Promise<ProfileWorkspaceResult> {
  const payload = await fetchNexoApi("/v1/profile");

  if (payload === null) {
    return {
      workspace: createDemoProfileWorkspace(),
      source: "demo",
    };
  }

  if (!isProfileWorkspace(payload)) {
    throw new Error("A API do NEXO retornou um perfil inválido.");
  }

  return {
    workspace: payload,
    source: "api",
  };
}
