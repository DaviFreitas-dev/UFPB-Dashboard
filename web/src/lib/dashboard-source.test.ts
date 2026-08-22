import { afterEach, describe, expect, it, vi } from "vitest";

import { loadTodayDashboard } from "./dashboard-source";
import { createDemoDashboard } from "./demo-dashboard";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadTodayDashboard", () => {
  it("usa a demonstração quando a API ainda não foi configurada", async () => {
    const result = await loadTodayDashboard();

    expect(result.source).toBe("demo");
  });

  it("não consulta uma API configurada sem o token do servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadTodayDashboard()).rejects.toThrow("token da API");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("envia o token e aceita o contrato completo", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const dashboard = createDemoDashboard(new Date(2026, 7, 22));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(dashboard), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadTodayDashboard();

    expect(result.source).toBe("api");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/dashboard/today",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Nexo-Token": "segredo-de-teste",
        },
      }),
    );
  });
});
