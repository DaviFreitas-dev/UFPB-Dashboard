import { afterEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";

import { fetchNexoApi, NexoApiError, requestNexoApi } from "./nexo-api";
import { CreateTaskResponseSchema } from "./task-mutation-contract";

const requireAuthorizedSessionMock = vi.mocked(requireAuthorizedSession);
const VALID_TASK_RESPONSE = {
  operationId: "task-request-1",
  created: true,
  task: {
    id: "0f3ac9b0-5779-40ce-834d-40a8657684af",
    date: "2026-08-23",
    title: "Revisar matemática",
    category: "Estudo",
    completed: false,
  },
};

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
      requestNexoApi(
        "/v1/tasks",
        { method: "POST", body: "{}" },
        CreateTaskResponseSchema,
      ),
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
    }, CreateTaskResponseSchema).catch((reason: unknown) => reason);

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
      requestNexoApi(
        "/v1/tasks",
        { method: "POST", body: "{}" },
        CreateTaskResponseSchema,
      ),
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
      }, CreateTaskResponseSchema).catch((reason: unknown) => reason);

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

  it.each([
    ["objeto vazio", {}],
    [
      "problema com status 2xx",
      {
        error: {
          code: "write_failed",
          message: "detalhe privado do upstream",
          operationId: "operation-private",
        },
      },
    ],
  ])("trata %s como falha ambígua sanitizada", async (_label, payload) => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(payload), { status: 200 }),
      ),
    );

    const error = await requestNexoApi(
      "/v1/tasks",
      { method: "POST", body: "{}" },
      CreateTaskResponseSchema,
    ).catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(NexoApiError);
    expect(error).toMatchObject({
      status: 200,
      code: "ambiguous_api_response",
      message: "Não foi possível confirmar a resposta da API.",
    });
    expect(String(error)).not.toContain("detalhe privado do upstream");
  });

  it.each([true, false])(
    "valida o contrato real de sucesso com created=%s",
    async (created) => {
      process.env.NEXO_API_URL = "http://127.0.0.1:8000";
      process.env.NEXO_API_TOKEN = "server-test";
      const expected = { ...VALID_TASK_RESPONSE, created };
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          new Response(JSON.stringify(expected), { status: 200 }),
        ),
      );

      await expect(
        requestNexoApi(
          "/v1/tasks",
          { method: "POST", body: "{}" },
          CreateTaskResponseSchema,
        ),
      ).resolves.toEqual(expected);
    },
  );

  it("mantém token e JSON somente na chamada do servidor", async () => {
    process.env.NEXO_API_URL = "http://127.0.0.1:8000";
    process.env.NEXO_API_TOKEN = "server-test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(VALID_TASK_RESPONSE), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestNexoApi(
      "/v1/tasks",
      { method: "POST", body: "{}" },
      CreateTaskResponseSchema,
    );

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
