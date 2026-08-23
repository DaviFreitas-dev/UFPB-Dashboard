import { beforeEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";

import { createTaskAction, initialCreateTaskState } from "./actions";

const { revalidatePath } = vi.hoisted(() => ({ revalidatePath: vi.fn() }));

vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/nexo-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/nexo-api")>();
  return { ...original, requestNexoApi: vi.fn() };
});

const requireAuthorizedSessionMock = vi.mocked(requireAuthorizedSession);

function validForm() {
  const form = new FormData();
  form.set("itemId", "0f3ac9b0-5779-40ce-834d-40a8657684af");
  form.set("title", "  Revisar matemática  ");
  form.set("category", "  Estudo  ");
  form.set("date", "2026-08-23");
  return form;
}

beforeEach(() => {
  requireAuthorizedSessionMock.mockReset();
  requireAuthorizedSessionMock.mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  } as never);
  vi.mocked(requestNexoApi).mockReset();
  revalidatePath.mockReset();
});

describe("createTaskAction", () => {
  it("revalida a autorização antes de ler o formulário", async () => {
    requireAuthorizedSessionMock.mockRejectedValue(
      new Error("Acesso não autorizado."),
    );
    const get = vi.fn(() => {
      throw new Error("O formulário não deveria ser lido.");
    });

    await expect(
      createTaskAction(initialCreateTaskState, { get } as unknown as FormData),
    ).rejects.toThrow("Acesso não autorizado.");
    expect(get).not.toHaveBeenCalled();
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("preserva o formulário quando o título está vazio", async () => {
    const form = validForm();
    form.set("title", "   ");

    const state = await createTaskAction(initialCreateTaskState, form);

    expect(state.status).toBe("error");
    expect(state.fieldErrors.title).toEqual(["Informe a tarefa."]);
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("recusa data inválida sem chamar a API", async () => {
    const form = validForm();
    form.set("date", "23/08/2026");

    const state = await createTaskAction(initialCreateTaskState, form);

    expect(state.fieldErrors.date).toEqual(["Informe uma data válida."]);
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("envia valores normalizados e revalida depois do sucesso", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({ created: true });

    const state = await createTaskAction(initialCreateTaskState, validForm());

    expect(requestNexoApi).toHaveBeenCalledWith("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        id: "0f3ac9b0-5779-40ce-834d-40a8657684af",
        date: "2026-08-23",
        title: "Revisar matemática",
        category: "Estudo",
      }),
    });
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
    expect(state.status).toBe("success");
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("traduz bloqueio de escrita sem perder o ID enviado", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(503, "writes_disabled", "blocked", "operation-1"),
    );

    const state = await createTaskAction(initialCreateTaskState, validForm());

    expect(state.message).toBe(
      "As alterações ainda não estão disponíveis nesta versão.",
    );
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(state.nextItemId).toBeNull();
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("traduz conflito de idempotência", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(
        409,
        "idempotency_conflict",
        "conflict",
        "operation-2",
      ),
    );

    const state = await createTaskAction(initialCreateTaskState, validForm());

    expect(state.message).toBe(
      "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente.",
    );
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("mantém o mesmo ID ao repetir uma falha ambígua", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(new Error("timeout interno"));
    const form = validForm();

    const first = await createTaskAction(initialCreateTaskState, form);
    const retry = await createTaskAction(first, form);

    expect(vi.mocked(requestNexoApi).mock.calls).toEqual([
      [
        "/v1/tasks",
        expect.objectContaining({
          body: expect.stringContaining(
            "0f3ac9b0-5779-40ce-834d-40a8657684af",
          ),
        }),
      ],
      [
        "/v1/tasks",
        expect.objectContaining({
          body: expect.stringContaining(
            "0f3ac9b0-5779-40ce-834d-40a8657684af",
          ),
        }),
      ],
    ]);
    expect(retry).toMatchObject({
      status: "error",
      message: "Não foi possível adicionar a tarefa agora.",
      submittedItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
      nextItemId: null,
    });
    expect(retry.message).not.toContain("timeout interno");
  });
});
