import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateHabitResponseSchema,
  HabitCheckinResponseSchema,
  HabitStateResponseSchema,
} from "@/lib/personal-mutation-contracts";

import {
  createHabitAction,
  setHabitActiveAction,
  setHabitCompletedAction,
} from "./habits";
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
const stableId = "398615a3-c08d-4f42-a9f4-b5d5c5c94515";

function createForm(name = "  Ler   vinte páginas  ") {
  const form = new FormData();
  form.set("itemId", stableId);
  form.set("name", name);
  return form;
}

function activeForm(active: string, configId = "habit-config-1") {
  const form = new FormData();
  form.set("configId", configId);
  form.set("active", active);
  return form;
}

function completedForm(completed: string, configId = "habit-config-1") {
  const form = new FormData();
  form.set("configId", configId);
  form.set("date", "2026-08-25");
  form.set("completed", completed);
  return form;
}

function createResponse(
  created = true,
  reactivated = false,
  habit: Partial<{ configId: string; title: string; active: boolean }> = {},
) {
  return {
    operationId: "habit-request-1",
    created,
    reactivated,
    habit: {
      configId: stableId,
      title: "Ler vinte páginas",
      active: true,
      ...habit,
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

describe("createHabitAction", () => {
  it("exige sessão e gate antes de ler o formulário", async () => {
    delete process.env.NEXO_WEB_WRITES_ENABLED;
    const get = vi.fn(() => {
      throw new Error("form must not be read");
    });

    const state = await createHabitAction(
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

  it.each([["   "], ["x".repeat(81)]])(
    "recusa nome inválido %j antes da API",
    async (name) => {
      const state = await createHabitAction(
        initialCreateMutationState,
        createForm(name),
      );

      expect(state.fieldErrors.name).toBeDefined();
      expect(state.submittedItemId).toBe(stableId);
      expect(requestNexoApi).not.toHaveBeenCalled();
    },
  );

  it("cria com nome normalizado, confirma a resposta e revalida", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(createResponse());

    const state = await createHabitAction(
      initialCreateMutationState,
      createForm(),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/habits",
      {
        method: "POST",
        body: JSON.stringify({ id: stableId, name: "Ler vinte páginas" }),
      },
      CreateHabitResponseSchema,
    );
    expect(state.status).toBe("success");
    expect(state.message).toBe("Hábito criado.");
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
    expect(revalidatePath.mock.calls).toEqual([["/habitos"], ["/"]]);
  });

  it.each([
    [false, true, "legacy-config", "Hábito reativado."],
    [false, false, "legacy-config", "Esse hábito já está ativo."],
  ] as const)(
    "aceita criação sem append created=%s reactivated=%s",
    async (created, reactivated, configId, message) => {
      vi.mocked(requestNexoApi).mockResolvedValue(
        createResponse(created, reactivated, {
          configId,
          title: "  LER   VINTE PÁGINAS ",
        }),
      );

      const state = await createHabitAction(
        initialCreateMutationState,
        createForm(),
      );

      expect(state).toMatchObject({ status: "success", message });
      expect(revalidatePath.mock.calls).toEqual([["/habitos"], ["/"]]);
    },
  );

  it("preserva nome e UUID depois de uma falha", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(new Error("timeout"));

    const state = await createHabitAction(
      initialCreateMutationState,
      createForm("Meditar"),
    );

    expect(state).toMatchObject({
      status: "error",
      submittedItemId: stableId,
      nextItemId: null,
    });
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it.each([
    { created: true, reactivated: true },
    { habit: { configId: "outro" } },
    { habit: { title: "Outro hábito" } },
    { habit: { active: false } },
  ])("não revalida uma resposta divergente %#", async (changes) => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      ...createResponse(),
      ...changes,
      habit: { ...createResponse().habit, ...changes.habit },
    });

    const state = await createHabitAction(
      initialCreateMutationState,
      createForm(),
    );

    expect(state.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("setHabitActiveAction", () => {
  it.each(["", "TRUE", "0", "false "])(
    "recusa active adulterado %j antes da API",
    async (active) => {
      const state = await setHabitActiveAction(
        initialInlineMutationState,
        activeForm(active),
      );

      expect(state.message).toBe("Revise os dados do hábito.");
      expect(requestNexoApi).not.toHaveBeenCalled();
    },
  );

  it("arquiva por estado desejado e exige confirmação exata", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "habit-request-1",
      changed: true,
      habit: { configId: "habit-config-1", title: "Ler", active: false },
    });

    const state = await setHabitActiveAction(
      initialInlineMutationState,
      activeForm("false"),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/habits/habit-config-1",
      { method: "PATCH", body: JSON.stringify({ active: false }) },
      HabitStateResponseSchema,
    );
    expect(state.message).toBe("Hábito arquivado.");
    expect(revalidatePath.mock.calls).toEqual([["/habitos"], ["/"]]);
  });

  it("não revalida estado divergente", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "habit-request-1",
      changed: false,
      habit: { configId: "habit-config-1", title: "Ler", active: true },
    });

    const state = await setHabitActiveAction(
      initialInlineMutationState,
      activeForm("false"),
    );

    expect(state.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("setHabitCompletedAction", () => {
  it.each(["", "TRUE", "yes", "false "])(
    "recusa completed adulterado %j antes da API",
    async (completed) => {
      const state = await setHabitCompletedAction(
        initialInlineMutationState,
        completedForm(completed),
      );

      expect(state.message).toBe("Revise os dados do hábito.");
      expect(requestNexoApi).not.toHaveBeenCalled();
    },
  );

  it("marca por data sem enviar ou inventar logId", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "habit-request-1",
      changed: true,
      checkin: {
        configId: "habit-config-1",
        logId: "habit-log-1",
        date: "2026-08-25",
        title: "Ler",
        completed: true,
      },
    });

    const state = await setHabitCompletedAction(
      initialInlineMutationState,
      completedForm("true"),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/habit-checkins/habit-config-1/2026-08-25",
      { method: "PUT", body: JSON.stringify({ completed: true }) },
      HabitCheckinResponseSchema,
    );
    expect(state.message).toBe("Hábito marcado como feito.");
    expect(revalidatePath.mock.calls).toEqual([["/habitos"], ["/"]]);
  });

  it("aceita logId ausente ao confirmar desmarcação sem log", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "habit-request-1",
      changed: false,
      checkin: {
        configId: "habit-config-1",
        logId: null,
        date: "2026-08-25",
        title: "Ler",
        completed: false,
      },
    });

    const state = await setHabitCompletedAction(
      initialInlineMutationState,
      completedForm("false"),
    );

    expect(state.message).toBe("Hábito desmarcado.");
    expect(revalidatePath.mock.calls).toEqual([["/habitos"], ["/"]]);
  });

  it.each([
    { configId: "outro" },
    { date: "2026-08-26" },
    { completed: false },
    { logId: null },
  ])("não revalida confirmação marcada divergente %#", async (checkin) => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "habit-request-1",
      changed: true,
      checkin: {
        configId: "habit-config-1",
        logId: "habit-log-1",
        date: "2026-08-25",
        title: "Ler",
        completed: true,
        ...checkin,
      },
    });

    const state = await setHabitCompletedAction(
      initialInlineMutationState,
      completedForm("true"),
    );

    expect(state.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("traduz gates e registro ausente sem expor mensagem interna", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(404, "record_not_found", "private"),
    );
    const missing = await setHabitCompletedAction(
      initialInlineMutationState,
      completedForm("true"),
    );
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(503, "writes_disabled", "private"),
    );
    const disabled = await setHabitCompletedAction(
      initialInlineMutationState,
      completedForm("true"),
    );

    expect(missing.message).toBe("O hábito não foi encontrado.");
    expect(disabled.message).toBe(
      "As alterações ainda não estão disponíveis nesta versão.",
    );
    expect(missing.message + disabled.message).not.toContain("private");
  });
});
