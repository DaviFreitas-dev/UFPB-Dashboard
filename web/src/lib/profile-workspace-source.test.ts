import { afterEach, describe, expect, it, vi } from "vitest";

import { createDemoProfileWorkspace } from "./demo-profile-workspace";
import { loadProfileWorkspace } from "./profile-workspace-source";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadProfileWorkspace", () => {
  it("usa a demonstração quando a API ainda não foi configurada", async () => {
    const result = await loadProfileWorkspace();

    expect(result.source).toBe("demo");
    expect(result.workspace.achievements.total).toBe(11);
  });

  it("envia o token do servidor e aceita o perfil completo", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const workspace = createDemoProfileWorkspace(new Date(2026, 7, 22));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadProfileWorkspace();

    expect(result.source).toBe("api");
    expect(result.workspace.settings.subjects[0]).toEqual({
      discipline: "Matemática",
      hours: 5,
      environment: "Mesa",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/profile",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Nexo-Token": "segredo-de-teste",
        },
      }),
    );
  });
});
