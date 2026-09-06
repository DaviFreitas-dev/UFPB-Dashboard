import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateTaskResponseSchema,
  DeleteTaskResponseSchema,
  TaskStateResponseSchema,
  type CreateTaskResponse,
} from "@/lib/personal-mutation-contracts";

import {
  createTaskAction,
  deleteTaskAction,
  setTaskCompletedAction,
} from "./tasks";
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

it("confirma tarefas legadas sem impor limites de cadastro na resposta", async () => {
  const id = "legacy/" + "x".repeat(100);
  const response = {
    operationId: "task-request-1", changed: true,
    task: { id, date: "2026-08-23", title: "a".repeat(200), category: "b".repeat(50), completed: true },
  };
  expect(TaskStateResponseSchema.safeParse(response).success).toBe(true);
  vi.mocked(requestNexoApi).mockResolvedValue(response);
  const form = taskForm();
  form.set("id", id);
  const result = await setTaskCompletedAction(initialInlineMutationState, form);
  expect(result.status).toBe("success");
  expect(requestNexoApi).toHaveBeenCalledWith(
    `/v1/tasks/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify({ completed: true }) }, TaskStateResponseSchema,
  );
});

function taskForm(completed: "true" | "false" = "true") {
  const form = new FormData();
  form.set("id", "task-1");
  form.set("completed", completed);
  return form;
}

function validCreateForm() {
  const form = new FormData();
  form.set("itemId", "0f3ac9b0-5779-40ce-834d-40a8657684af");
  form.set("title", "  Revisar matemática  ");
  form.set("category", "  Estudo  ");
  form.set("date", "2026-08-23");
  return form;
}

function confirmedCreateResponse(
  created = true,
  task: Partial<CreateTaskResponse["task"]> = {},
): CreateTaskResponse {
  return {
    operationId: "task-request-1",
    created,
    task: {
      id: "0f3ac9b0-5779-40ce-834d-40a8657684af",
      date: "2026-08-23",
      title: "Revisar matemática",
      category: "Estudo",
      completed: false,
      ...task,
    },
  };
}

function deleteForm() {
  const form = new FormData();
  form.set("id", "task-1");
  return form;
}

function confirmedTaskState(completed: boolean) {
  return {
    operationId: "task-request-1",
    changed: true,
    task: {
      id: "task-1",
      date: "2026-08-23",
      title: "Revisar matemática",
      category: "Estudo",
      completed,
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

describe("createTaskAction", () => {
  it("revalida a autorização antes de ler o formulário", async () => {
    delete process.env.NEXO_WEB_WRITES_ENABLED;
    requireAuthorizedSessionMock.mockRejectedValue(
      new Error("Acesso não autorizado."),
    );
    const get = vi.fn(() => {
      throw new Error("O formulário não deveria ser lido.");
    });

    await expect(
      createTaskAction(
        initialCreateMutationState,
        { get } as unknown as FormData,
      ),
    ).rejects.toThrow("Acesso não autorizado.");
    expect(get).not.toHaveBeenCalled();
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it.each([undefined, "false"])(
    "bloqueia invocação direta antes de ler o formulário com flag %s",
    async (flag) => {
      if (flag === undefined) {
        delete process.env.NEXO_WEB_WRITES_ENABLED;
      } else {
        process.env.NEXO_WEB_WRITES_ENABLED = flag;
      }
      const get = vi.fn(() => {
        throw new Error("O formulário não deveria ser lido.");
      });

      const state = await createTaskAction(
        initialCreateMutationState,
        { get } as unknown as FormData,
      );

      expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
      expect(get).not.toHaveBeenCalled();
      expect(requestNexoApi).not.toHaveBeenCalled();
      expect(state).toMatchObject({
        status: "error",
        message: "As alterações ainda não estão disponíveis nesta versão.",
        submittedItemId: null,
        nextItemId: null,
      });
    },
  );

  it("preserva o formulário quando o título está vazio", async () => {
    const form = validCreateForm();
    form.set("title", "   ");

    const state = await createTaskAction(initialCreateMutationState, form);

    expect(state.status).toBe("error");
    expect(state.fieldErrors.title).toEqual(["Informe a tarefa."]);
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("recusa data inválida sem chamar a API", async () => {
    const form = validCreateForm();
    form.set("date", "23/08/2026");

    const state = await createTaskAction(initialCreateMutationState, form);

    expect(state.fieldErrors.date).toEqual(["Informe uma data válida."]);
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("renova um UUID adulterado e permite tentar novamente", async () => {
    const form = validCreateForm();
    form.set("itemId", "id-adulterado");

    const invalidState = await createTaskAction(initialCreateMutationState, form);

    expect(invalidState).toMatchObject({
      status: "error",
      message: "O formulário foi renovado. Revise os campos e tente novamente.",
      nextItemId: null,
    });
    expect(invalidState.submittedItemId).toMatch(/^[0-9a-f-]{36}$/);
    expect(invalidState.submittedItemId).not.toBe("id-adulterado");
    expect(requestNexoApi).not.toHaveBeenCalled();

    form.set("itemId", invalidState.submittedItemId as string);
    vi.mocked(requestNexoApi).mockResolvedValue(
      confirmedCreateResponse(true, {
        id: invalidState.submittedItemId as string,
      }),
    );
    const retryState = await createTaskAction(invalidState, form);

    expect(retryState.status).toBe("success");
    expect(requestNexoApi).toHaveBeenCalledOnce();
  });

  it("envia valores normalizados e revalida depois do sucesso", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedCreateResponse());

    const state = await createTaskAction(
      initialCreateMutationState,
      validCreateForm(),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/tasks",
      {
        method: "POST",
        body: JSON.stringify({
          id: "0f3ac9b0-5779-40ce-834d-40a8657684af",
          date: "2026-08-23",
          title: "Revisar matemática",
          category: "Estudo",
        }),
      },
      CreateTaskResponseSchema,
    );
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
    expect(state.status).toBe("success");
    expect(state.submittedItemId).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("trata created=false como replay confirmado e gira o UUID", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedCreateResponse(false));

    const state = await createTaskAction(
      initialCreateMutationState,
      validCreateForm(),
    );

    expect(state).toMatchObject({
      status: "success",
      message: "Tarefa adicionada.",
      submittedItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
    });
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
    expect(state.nextItemId).not.toBe(state.submittedItemId);
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
  });

  it.each([
    ["id", "b6f79644-8787-40a7-8d5d-4f83078657ab"],
    ["date", "2026-08-24"],
    ["title", "Outra tarefa"],
    ["category", "Pessoal"],
  ] as const)(
    "trata divergência do campo imutável %s como falha ambígua",
    async (field, value) => {
      vi.mocked(requestNexoApi).mockResolvedValue(
        confirmedCreateResponse(true, { [field]: value }),
      );

      const state = await createTaskAction(
        initialCreateMutationState,
        validCreateForm(),
      );

      expect(state).toMatchObject({
        status: "error",
        message:
          "Não foi possível confirmar se a tarefa foi salva. Tente novamente.",
        submittedItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
        nextItemId: null,
      });
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );

  it("preserva o UUID quando um 2xx não confirma o contrato", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(200, "ambiguous_api_response", "detalhe privado"),
    );

    const state = await createTaskAction(
      initialCreateMutationState,
      validCreateForm(),
    );

    expect(state).toMatchObject({
      status: "error",
      message:
        "Não foi possível confirmar se a tarefa foi salva. Tente novamente.",
      submittedItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
      nextItemId: null,
    });
    expect(state.message).not.toContain("detalhe privado");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("traduz bloqueio de escrita sem perder o ID enviado", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(503, "writes_disabled", "blocked", "operation-1"),
    );

    const state = await createTaskAction(
      initialCreateMutationState,
      validCreateForm(),
    );

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

    const state = await createTaskAction(
      initialCreateMutationState,
      validCreateForm(),
    );

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
    const form = validCreateForm();

    const first = await createTaskAction(initialCreateMutationState, form);
    const retry = await createTaskAction(first, form);

    expect(vi.mocked(requestNexoApi).mock.calls).toEqual([
      [
        "/v1/tasks",
        expect.objectContaining({
          body: expect.stringContaining(
            "0f3ac9b0-5779-40ce-834d-40a8657684af",
          ),
        }),
        CreateTaskResponseSchema,
      ],
      [
        "/v1/tasks",
        expect.objectContaining({
          body: expect.stringContaining(
            "0f3ac9b0-5779-40ce-834d-40a8657684af",
          ),
        }),
        CreateTaskResponseSchema,
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

describe("task lifecycle actions", () => {
  it.each([setTaskCompletedAction, deleteTaskAction])(
    "exige a sessão antes de consultar o gate ou o formulário",
    async (action) => {
      delete process.env.NEXO_WEB_WRITES_ENABLED;
      requireAuthorizedSessionMock.mockRejectedValue(
        new Error("Acesso não autorizado."),
      );
      const get = vi.fn(() => {
        throw new Error("O formulário não deveria ser lido.");
      });

      await expect(
        action(
          initialInlineMutationState,
          { get } as unknown as FormData,
        ),
      ).rejects.toThrow("Acesso não autorizado.");
      expect(get).not.toHaveBeenCalled();
      expect(requestNexoApi).not.toHaveBeenCalled();
    },
  );

  it.each([setTaskCompletedAction, deleteTaskAction])(
    "verifica o gate web antes de ler FormData",
    async (action) => {
      delete process.env.NEXO_WEB_WRITES_ENABLED;
      const get = vi.fn(() => {
        throw new Error("O formulário não deveria ser lido.");
      });

      const state = await action(
        initialInlineMutationState,
        { get } as unknown as FormData,
      );

      expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
      expect(get).not.toHaveBeenCalled();
      expect(requestNexoApi).not.toHaveBeenCalled();
      expect(state).toEqual({
        status: "error",
        message: "As alterações ainda não estão disponíveis nesta versão.",
      });
    },
  );

  it.each(["", "TRUE", "yes", "0", "false "])(
    "recusa completed adulterado %j sem converter silenciosamente para false",
    async (completed) => {
      const form = taskForm();
      form.set("completed", completed);

      const state = await setTaskCompletedAction(
        initialInlineMutationState,
        form,
      );

      expect(state).toEqual({
        status: "error",
        message: "Revise os dados da tarefa.",
      });
      expect(requestNexoApi).not.toHaveBeenCalled();
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );

  it("envia o estado desejado e revalida somente após confirmação", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue(confirmedTaskState(true));

    const state = await setTaskCompletedAction(
      initialInlineMutationState,
      taskForm("true"),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/tasks/task-1",
      {
        method: "PATCH",
        body: JSON.stringify({ completed: true }),
      },
      TaskStateResponseSchema,
    );
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
    expect(state).toEqual({
      status: "success",
      message: "Tarefa concluída.",
    });
  });

  it("aceita replay confirmado ao reabrir", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      ...confirmedTaskState(false),
      changed: false,
    });

    const state = await setTaskCompletedAction(
      initialInlineMutationState,
      taskForm("false"),
    );

    expect(state).toEqual({
      status: "success",
      message: "Tarefa reaberta.",
    });
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
  });

  it.each([
    ["id", "task-2"],
    ["completed", false],
  ] as const)(
    "não revalida quando a resposta diverge em %s",
    async (field, value) => {
      const response = confirmedTaskState(true);
      response.task = { ...response.task, [field]: value };
      vi.mocked(requestNexoApi).mockResolvedValue(response);

      const state = await setTaskCompletedAction(
        initialInlineMutationState,
        taskForm("true"),
      );

      expect(state).toEqual({
        status: "error",
        message: "Não foi possível atualizar a tarefa agora.",
      });
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );

  it("mapeia falhas sem expor detalhes internos", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(
      new NexoApiError(
        503,
        "write_failed",
        "segredo interno da planilha",
        "operation-1",
      ),
    );

    const state = await setTaskCompletedAction(
      initialInlineMutationState,
      taskForm(),
    );

    expect(state).toEqual({
      status: "error",
      message: "Não foi possível atualizar a tarefa agora.",
    });
    expect(state.message).not.toContain("segredo interno da planilha");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("exclui pelo caminho exato e confirma a resposta", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "task-request-1",
      id: "task-1",
      deleted: true,
    });

    const state = await deleteTaskAction(
      initialInlineMutationState,
      deleteForm(),
    );

    expect(requestNexoApi).toHaveBeenCalledWith(
      "/v1/tasks/task-1",
      { method: "DELETE" },
      DeleteTaskResponseSchema,
    );
    expect(state).toEqual({
      status: "success",
      message: "Tarefa excluída.",
    });
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
  });

  it("aceita exclusão repetida como estado final confirmado", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "task-request-1",
      id: "task-1",
      deleted: false,
    });

    const state = await deleteTaskAction(
      initialInlineMutationState,
      deleteForm(),
    );

    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/tarefas"], ["/"]]);
  });

  it("recusa confirmação de exclusão para outro ID", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "task-request-1",
      id: "task-2",
      deleted: true,
    });

    const state = await deleteTaskAction(
      initialInlineMutationState,
      deleteForm(),
    );

    expect(state).toEqual({
      status: "error",
      message: "Não foi possível excluir a tarefa agora.",
    });
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});
