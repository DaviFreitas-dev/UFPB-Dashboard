import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateRoutineItemResponseSchema,
  DeleteRoutineItemResponseSchema,
  RoutineItemStateResponseSchema,
  type CreateRoutineItemResponse,
} from "@/lib/personal-mutation-contracts";

import {
  createRoutineItemAction,
  deleteRoutineItemAction,
  setRoutineItemCompletedAction,
} from "./routine";
import {
  initialCreateMutationState,
  initialInlineMutationState,
} from "./mutation-state";

const { revalidatePath } = vi.hoisted(() => ({ revalidatePath: vi.fn() }));

vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/nexo-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/nexo-api")>();
  return { ...original, requestNexoApi: vi.fn() };
});

const requireAuthorizedSessionMock = vi.mocked(requireAuthorizedSession);
const stableId = "0f3ac9b0-5779-40ce-834d-40a8657684af";

function validCreateForm() {
  const form = new FormData();
  form.set("itemId", stableId);
  form.set("title", "  Dentista  ");
  form.set("time", " 08:30 ");
  form.set("date", "2026-08-25");
  return form;
}

function confirmedCreateResponse(
  created = true,
  item: Partial<CreateRoutineItemResponse["item"]> = {},
): CreateRoutineItemResponse {
  return {
    operationId: "routine-request-1",
    created,
    item: {
      id: stableId,
      date: "2026-08-25",
      time: "08:30",
      title: "Dentista",
      completed: false,
      ...item,
    },
  };
}

function stateForm(completed: string, id = "routine-1") {
  const form = new FormData();
  form.set("id", id);
  form.set("completed", completed);
  return form;
}

function deleteForm(id = "routine-1") {
  const form = new FormData();
  form.set("id", id);
  return form;
}

function confirmedState(
  completed: boolean,
  item: Partial<{
    id: string;
    date: string;
    time: string;
    title: string;
    completed: boolean;
  }> = {},
) {
  return {
    operationId: "routine-request-1",
    changed: true,
    item: {
      id: "routine-1",
      date: "2026-08-25",
      time: "08:30",
      title: "Dentista",
      completed,
      ...item,
    },
  };
}

beforeEach(() => {
  process.env.NEXO_WEB_WRITES_ENABLED = "true";
  requireAuthorizedSessionMock.mockReset();
  requireAuthorizedSessionMock.mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  } as never);
  vi.mocked(requestNexoApi).mockReset();
  revalidatePath.mockReset();
});

afterEach(() => {
  delete process.env.NEXO_WEB_WRITES_ENABLED;
});

describe("createRoutineItemAction", () => {
  it("exige a sessão e o gate antes de ler o formulário", async () => {
    delete process.env.NEXO_WEB_WRITES_ENABLED;
    const get = vi.fn(() => {
      throw new Error("form must not be read");
    });

    const state = await createRoutineItemAction(
      initialCreateMutationState,
      { get } as unknown as FormData,
    );

    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
    expect(get).not.toHaveBeenCalled();
    expect(requestNexoApi).not.toHaveBeenCalled();
    expect(state.message).toBe(
      "As alterações ainda não estão disponíveis nesta versão.",
    );
  });

  it.each([
    ["time", "8:30", "Informe um horário válido no formato HH:MM."],
    ["time", "24:00", "Informe um horário válido no formato HH:MM."],
    ["date", "25/08/2026", "Informe uma data válida."],
    ["title", "   ", "Informe a atividade."],
  ])("recusa %s inválido antes da API", async (field, value, message) => {
    const form = validCreateForm();
    form.set(field, value);

    const state = await createRoutineItemAction(
      initialCreateMutationState,
      form,
    );

    expect(state.fieldErrors[field]).toEqual([message]);
    expect(state.submittedItemId).toBe(stableId);
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("envia campos normalizados e revalida exatamente as duas rotas", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedCreateResponse());

    const state = await createRoutineItemAction(
      initialCreateMutationState,
      validCreateForm(),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/routine-items",
      {
        method: "POST",
        body: JSON.stringify({
          id: stableId,
          date: "2026-08-25",
          time: "08:30",
          title: "Dentista",
        }),
      },
      CreateRoutineItemResponseSchema,
    );
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
    expect(state.status).toBe("success");
    expect(state.submittedItemId).toBe(stableId);
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
    expect(state.nextItemId).not.toBe(stableId);
  });

  it("mantém o UUID estável em falha e em nova tentativa", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(new Error("timeout"));
    const form = validCreateForm();

    const first = await createRoutineItemAction(
      initialCreateMutationState,
      form,
    );
    const retry = await createRoutineItemAction(first, form);

    expect(vi.mocked(requestNexoApi).mock.calls).toHaveLength(2);
    for (const call of vi.mocked(requestNexoApi).mock.calls) {
      expect(call[1]?.body).toContain(stableId);
    }
    expect(retry).toMatchObject({
      status: "error",
      submittedItemId: stableId,
      nextItemId: null,
    });
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it.each([
    ["id", "b6f79644-8787-40a7-8d5d-4f83078657ab"],
    ["date", "2026-08-26"],
    ["time", "09:00"],
    ["title", "Mercado"],
  ] as const)(
    "não gira UUID nem revalida quando a resposta diverge em %s",
    async (field, value) => {
      vi.mocked(requestNexoApi).mockResolvedValue(
        confirmedCreateResponse(true, { [field]: value }),
      );

      const state = await createRoutineItemAction(
        initialCreateMutationState,
        validCreateForm(),
      );

      expect(state).toMatchObject({
        status: "error",
        submittedItemId: stableId,
        nextItemId: null,
      });
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );

  it("traduz conflito de idempotência sem perder o UUID", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(409, "idempotency_conflict", "private"),
    );

    const state = await createRoutineItemAction(
      initialCreateMutationState,
      validCreateForm(),
    );

    expect(state.message).toContain("outros dados");
    expect(state.message).not.toContain("private");
    expect(state.submittedItemId).toBe(stableId);
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("routine lifecycle actions", () => {
  it("limita a identidade persistente a 512 caracteres nos contratos", () => {
    const acceptedId = "i".repeat(512);
    const rejectedId = "i".repeat(513);

    expect(
      RoutineItemStateResponseSchema.safeParse(
        confirmedState(true, { id: acceptedId }),
      ).success,
    ).toBe(true);
    expect(
      DeleteRoutineItemResponseSchema.safeParse({
        operationId: "routine-request-1",
        id: acceptedId,
        deleted: true,
      }).success,
    ).toBe(true);
    expect(
      RoutineItemStateResponseSchema.safeParse(
        confirmedState(true, { id: rejectedId }),
      ).success,
    ).toBe(false);
    expect(
      DeleteRoutineItemResponseSchema.safeParse({
        operationId: "routine-request-1",
        id: rejectedId,
        deleted: true,
      }).success,
    ).toBe(false);
  });

  it("aceita contratos legados longos apenas na confirmação de registros existentes", () => {
    const legacyId = `legacy/${"i".repeat(90)}`;
    const legacyTime = `horário legado ${"h".repeat(40)}`;
    const legacyTitle = `Compromisso legado ${"t".repeat(160)}`;

    expect(
      RoutineItemStateResponseSchema.safeParse(
        confirmedState(true, {
          id: legacyId,
          time: legacyTime,
          title: legacyTitle,
        }),
      ).success,
    ).toBe(true);
    expect(
      DeleteRoutineItemResponseSchema.safeParse({
        operationId: "routine-request-1",
        id: legacyId,
        deleted: true,
      }).success,
    ).toBe(true);
    expect(
      CreateRoutineItemResponseSchema.safeParse(
        confirmedCreateResponse(true, { title: legacyTitle }),
      ).success,
    ).toBe(false);
  });

  it("aceita horário legado na confirmação de uma mudança de estado", () => {
    expect(
      RoutineItemStateResponseSchema.safeParse({
        ...confirmedState(true),
        item: { ...confirmedState(true).item, time: "sem-hora" },
      }).success,
    ).toBe(true);
    expect(
      CreateRoutineItemResponseSchema.safeParse(
        confirmedCreateResponse(true, { time: "sem-hora" }),
      ).success,
    ).toBe(false);
  });

  it.each(["", "TRUE", "yes", "0", "false "])(
    "recusa completed adulterado %j antes da API",
    async (completed) => {
      const state = await setRoutineItemCompletedAction(
        initialInlineMutationState,
        stateForm(completed),
      );

      expect(state).toEqual({
        status: "error",
        message: "Revise os dados do compromisso.",
      });
      expect(requestNexoApi).not.toHaveBeenCalled();
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );

  it("envia o estado desejado e revalida após confirmação", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedState(false));

    const state = await setRoutineItemCompletedAction(
      initialInlineMutationState,
      stateForm("false"),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/routine-items/routine-1",
      {
        method: "PATCH",
        body: JSON.stringify({ completed: false }),
      },
      RoutineItemStateResponseSchema,
    );
    expect(state.message).toBe("Compromisso reaberto.");
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
  });

  it("altera um ID persistente longo e aceita a confirmação legada longa", async () => {
    const legacyId = `legacy/${"i".repeat(90)}`;
    const response = confirmedState(true, {
      id: legacyId,
      time: `horário legado ${"h".repeat(40)}`,
      title: `Compromisso legado ${"t".repeat(160)}`,
    });
    vi.mocked(requestNexoApi).mockImplementation(
      async (_path, _init, responseSchema) => responseSchema.parse(response),
    );

    const state = await setRoutineItemCompletedAction(
      initialInlineMutationState,
      stateForm("true", legacyId),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      `/v1/routine-items/${encodeURIComponent(legacyId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ completed: true }),
      },
      RoutineItemStateResponseSchema,
    );
    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
  });

  it("altera uma identidade persistente no teto seguro", async () => {
    const itemId = "i".repeat(512);
    vi.mocked(requestNexoApi).mockResolvedValue(
      confirmedState(true, { id: itemId }),
    );

    const state = await setRoutineItemCompletedAction(
      initialInlineMutationState,
      stateForm("true", itemId),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      `/v1/routine-items/${itemId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ completed: true }),
      },
      RoutineItemStateResponseSchema,
    );
    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
  });

  it("recusa identidades acima do teto antes da API", async () => {
    const itemId = "i".repeat(513);

    const state = await setRoutineItemCompletedAction(
      initialInlineMutationState,
      stateForm("true", itemId),
    );
    const deleteState = await deleteRoutineItemAction(
      initialInlineMutationState,
      deleteForm(itemId),
    );

    expect(state).toEqual({
      status: "error",
      message: "Revise os dados do compromisso.",
    });
    expect(deleteState).toEqual(state);
    expect(requestNexoApi).not.toHaveBeenCalled();
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("não revalida uma resposta com estado divergente", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedState(false));

    const state = await setRoutineItemCompletedAction(
      initialInlineMutationState,
      stateForm("true"),
    );

    expect(state.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it.each([true, false])(
    "confirma exclusão deleted=%s e revalida",
    async (deleted) => {
      vi.mocked(requestNexoApi).mockResolvedValue({
        operationId: "routine-request-1",
        id: "routine-1",
        deleted,
      });

      const state = await deleteRoutineItemAction(
        initialInlineMutationState,
        deleteForm(),
      );

      expect(requestNexoApi).toHaveBeenCalledWith(
        "/v1/routine-items/routine-1",
        { method: "DELETE" },
        DeleteRoutineItemResponseSchema,
      );
      expect(state).toEqual({
        status: "success",
        message: "Compromisso excluído.",
      });
      expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
    },
  );

  it("exclui um ID persistente longo com URL segura", async () => {
    const legacyId = `legacy/${"i".repeat(90)}`;
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "routine-request-1",
      id: legacyId,
      deleted: true,
    });

    const state = await deleteRoutineItemAction(
      initialInlineMutationState,
      deleteForm(legacyId),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      `/v1/routine-items/${encodeURIComponent(legacyId)}`,
      { method: "DELETE" },
      DeleteRoutineItemResponseSchema,
    );
    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
  });

  it("exclui uma identidade persistente no teto seguro", async () => {
    const itemId = "i".repeat(512);
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "routine-request-1",
      id: itemId,
      deleted: true,
    });

    const state = await deleteRoutineItemAction(
      initialInlineMutationState,
      deleteForm(itemId),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      `/v1/routine-items/${itemId}`,
      { method: "DELETE" },
      DeleteRoutineItemResponseSchema,
    );
    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/rotina"], ["/"]]);
  });

  it("recusa confirmação de exclusão para outro ID", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "routine-request-1",
      id: "routine-2",
      deleted: true,
    });

    const state = await deleteRoutineItemAction(
      initialInlineMutationState,
      deleteForm(),
    );

    expect(state.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});
