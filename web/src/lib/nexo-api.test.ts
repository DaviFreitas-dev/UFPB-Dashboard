import { afterEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";

import { fetchNexoApi, NexoApiError, requestNexoApi } from "./nexo-api";

const requireAuthorizedSessionMock = vi.mocked(requireAuthorizedSession);

afterEach(() => {
  requireAuthorizedSessionMock.mockReset();
  requireAuthorizedSessionMock.mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  } as never);
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("fetchNexoApi", () => {
  it("revalida a sessão antes mesmo de decidir pelo fallback local", async () => {
    requireAuthorizedSessionMock.mockRejectedValue(
      new Error("Acesso não autorizado."),
    );
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchNexoApi("/v1/dashboard/today")).rejects.toThrow(
      "Acesso não autorizado.",
    );
    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("mantém o fallback sem API para uma sessão autorizada", async () => {
    await expect(fetchNexoApi("/v1/dashboard/today")).resolves.toBeNull();
    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
  });
});

describe("requestNexoApi", () => {
  it("recusa a mutação antes de consultar configuração ou rede", async () => {
    requireAuthorizedSessionMock.mockRejectedValue(
      new Error("Acesso não autorizado."),
    );
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      requestNexoApi("/v1/tasks", { method: "POST", body: "{}" }),
    ).rejects.toThrow("Acesso não autorizado.");
    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("traduz um conflito seguro da API", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "idempotency_conflict",
              message: "Esta operação já foi usada com outro conteúdo.",
              operationId: "operation-1",
            },
          }),
          { status: 409 },
        ),
      ),
    );

    const error = await requestNexoApi("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({ id: "task-1" }),
    }).catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(NexoApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "idempotency_conflict",
      operationId: "operation-1",
    });
  });

  it("usa erro seguro quando a API não devolve um problema estruturado", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "internals" }), { status: 500 }),
      ),
    );

    await expect(
      requestNexoApi("/v1/tasks", { method: "POST", body: "{}" }),
    ).rejects.toMatchObject({
      status: 500,
      code: "unexpected_api_error",
      message: "Não foi possível concluir a operação.",
    });
  });

  it.each([
    [502, "<html>segredo interno do proxy</html>", "text/html"],
    [503, "segredo interno do upstream", "text/plain"],
  ])(
    "sanitiza uma resposta %i que não é JSON",
    async (status, body, contentType) => {
      process.env.NEXO_API_URL = "http://127.0.0.1:8000";
      process.env.NEXO_API_TOKEN = "server-test";
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          new Response(body, {
            status,
            headers: { "Content-Type": contentType },
          }),
        ),
      );

      const error = await requestNexoApi("/v1/tasks", {
        method: "POST",
        body: "{}",
      }).catch((reason: unknown) => reason);

      expect(error).toBeInstanceOf(NexoApiError);
      expect(error).toMatchObject({
        status,
        code: "unexpected_api_error",
        message: "Não foi possível concluir a operação.",
      });
      expect(error).not.toBeInstanceOf(SyntaxError);
      expect(String(error)).not.toContain(body);
    },
  );

  it("mantém token e JSON somente na chamada do servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestNexoApi("/v1/tasks", { method: "POST", body: "{}" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/v1/tasks",
      expect.objectContaining({
        cache: "no-store",
        method: "POST",
        body: "{}",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Nexo-Token": "server-test",
        }),
      }),
    );
  });
});
