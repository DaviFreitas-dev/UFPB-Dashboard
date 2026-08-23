import { afterEach, describe, expect, it, vi } from "vitest";

import { createDemoRoutine } from "./demo-routine";
import { loadRoutineDashboard } from "./routine-source";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadRoutineDashboard", () => {
  it("usa dados de demonstração para a data escolhida sem API", async () => {
    const result = await loadRoutineDashboard("2026-08-24");

    expect(result.source).toBe("demo");
    expect(result.routine.date).toBe("2026-08-24");
  });

  it("envia data e token somente pelo servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const routine = createDemoRoutine(new Date(2026, 7, 24));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(routine), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadRoutineDashboard("2026-08-24");

    expect(result.source).toBe("api");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/routine?date=2026-08-24",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Nexo-Token": "segredo-de-teste",
        },
      }),
    );
  });

  it("deixa a API escolher o dia atual quando não há data na URL", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const routine = createDemoRoutine(new Date(2026, 7, 24));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(routine), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loadRoutineDashboard();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/routine",
      expect.any(Object),
    );
  });
});
