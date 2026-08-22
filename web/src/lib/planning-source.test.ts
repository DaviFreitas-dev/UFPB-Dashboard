import { afterEach, describe, expect, it, vi } from "vitest";

import { createDemoPlanning } from "./demo-planning";
import { loadPlanningDashboard } from "./planning-source";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadPlanningDashboard", () => {
  it("usa a demonstração enquanto a API não está configurada", async () => {
    const result = await loadPlanningDashboard();

    expect(result.source).toBe("demo");
    expect(result.planning.week).toHaveLength(7);
  });

  it("não faz a consulta sem o token do servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadPlanningDashboard()).rejects.toThrow("token da API");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("envia o token e valida o contrato", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const planning = createDemoPlanning(new Date(2026, 7, 22));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(planning), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadPlanningDashboard();

    expect(result.source).toBe("api");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/planning",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Nexo-Token": "segredo-de-teste",
        },
      }),
    );
  });
});
