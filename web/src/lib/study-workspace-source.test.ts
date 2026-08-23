import { afterEach, describe, expect, it, vi } from "vitest";

import { createDemoStudyWorkspace } from "./demo-study-workspace";
import { loadStudyWorkspace } from "./study-workspace-source";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadStudyWorkspace", () => {
  it("usa a demonstração enquanto a API não está configurada", async () => {
    const result = await loadStudyWorkspace();

    expect(result.source).toBe("demo");
    expect(result.studies.cycle.subjects.length).toBeGreaterThan(0);
  });

  it("envia o token e aceita o contrato de estudos", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const workspace = createDemoStudyWorkspace(new Date(2026, 7, 22));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadStudyWorkspace();

    expect(result.source).toBe("api");
    expect(result.studies.date).toBe("2026-08-22");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/studies",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Nexo-Token": "segredo-de-teste",
        },
      }),
    );
  });
});
