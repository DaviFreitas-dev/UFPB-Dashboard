import { afterEach, describe, expect, it, vi } from "vitest";

import { createDemoPersonalWorkspace } from "./demo-personal-workspace";
import { loadPersonalWorkspace } from "./personal-workspace-source";

afterEach(() => {
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("loadPersonalWorkspace", () => {
  it("usa a demonstração para a data escolhida sem API", async () => {
    const result = await loadPersonalWorkspace("2026-08-24");

    expect(result.source).toBe("demo");
    expect(result.workspace.date).toBe("2026-08-24");
  });

  it("envia a data e o token somente pelo servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000/";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    const workspace = createDemoPersonalWorkspace(new Date(2026, 7, 24));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadPersonalWorkspace("2026-08-24");

    expect(result.source).toBe("api");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/personal?date=2026-08-24",
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
    const workspace = createDemoPersonalWorkspace(new Date(2026, 7, 24));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loadPersonalWorkspace();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/personal",
      expect.any(Object),
    );
  });

  it("recusa um contrato inválido vindo da API", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "segredo-de-teste";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ date: "2026-08-24" }), { status: 200 }),
      ),
    );

    await expect(loadPersonalWorkspace("2026-08-24")).rejects.toThrow(
      "dados pessoais inválidos",
    );
  });
});
