import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateBookResponseSchema,
  DeleteBookResponseSchema,
  UpdateBookResponseSchema,
} from "@/lib/personal-mutation-contracts";
import { initialCreateMutationState, initialInlineMutationState } from "./mutation-state";
import { createBookAction, deleteBookAction, updateBookAction } from "./reading";

const { revalidatePath } = vi.hoisted(() => ({ revalidatePath: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/nexo-api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/nexo-api")>();
  return { ...original, requestNexoApi: vi.fn() };
});

const createId = "0f3ac9b0-5779-40ce-834d-40a8657684af";

function createForm() {
  const form = new FormData();
  form.set("itemId", createId);
  form.set("title", "  O Hobbit  ");
  form.set("author", "  Tolkien  ");
  form.set("totalPages", "320");
  form.set("dailyGoal", "20");
  return form;
}

function updateForm(values: Record<string, string> = { currentPage: "64", totalPages: "320" }) {
  const form = new FormData();
  form.set("id", "book-1");
  for (const [key, value] of Object.entries(values)) form.set(key, value);
  return form;
}

function book(overrides: Record<string, unknown> = {}) {
  return {
    id: "book-1", title: "O Hobbit", author: "Tolkien", currentPage: 64,
    totalPages: 320, dailyGoal: 20, status: "Lendo", ...overrides,
  };
}

beforeEach(() => {
  process.env.NEXO_WEB_WRITES_ENABLED = "true";
  vi.mocked(requireAuthorizedSession).mockReset();
  vi.mocked(requireAuthorizedSession).mockResolvedValue({ user: {} } as never);
  vi.mocked(requestNexoApi).mockReset();
  revalidatePath.mockReset();
});

afterEach(() => delete process.env.NEXO_WEB_WRITES_ENABLED);

describe("createBookAction", () => {
  it("preserva o UUID estável em falhas e envia números normalizados", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(new Error("falha privada"));
    const form = createForm();

    const first = await createBookAction(initialCreateMutationState, form);
    const retry = await createBookAction(first, form);

    expect(vi.mocked(requestNexoApi).mock.calls).toEqual([
      ["/v1/books", expect.objectContaining({ body: JSON.stringify({ id: createId, title: "O Hobbit", author: "Tolkien", totalPages: 320, dailyGoal: 20 }) }), CreateBookResponseSchema],
      ["/v1/books", expect.objectContaining({ body: JSON.stringify({ id: createId, title: "O Hobbit", author: "Tolkien", totalPages: 320, dailyGoal: 20 }) }), CreateBookResponseSchema],
    ]);
    expect(retry.submittedItemId).toBe(createId);
    expect(retry.nextItemId).toBeNull();
    expect(retry.message).not.toContain("privada");
  });

  it.each([
    ["title", "", "Informe o título."],
    ["totalPages", "0", "Informe um total positivo."],
    ["dailyGoal", "1.5", "Informe uma meta inteira positiva."],
  ])("devolve erro de campo para %s", async (field, value, expected) => {
    const form = createForm();
    form.set(field, value);
    const state = await createBookAction(initialCreateMutationState, form);
    expect(state.fieldErrors[field]).toContain(expected);
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it("confirma criação, gira o UUID e revalida apenas leitura e Hoje", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "reading-request-1", created: false,
      book: { id: createId, title: "O Hobbit", author: "Tolkien", currentPage: 0, totalPages: 320, dailyGoal: 20, status: "Lendo" },
    });
    const state = await createBookAction(initialCreateMutationState, createForm());
    expect(state.status).toBe("success");
    expect(state.nextItemId).toMatch(/^[0-9a-f-]{36}$/);
    expect(state.nextItemId).not.toBe(createId);
    expect(revalidatePath.mock.calls).toEqual([["/leitura"], ["/"]]);
  });

  it("recusa resposta divergente sem revalidar", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "reading-request-1", created: true,
      book: { id: createId, title: "Outro", author: "Tolkien", currentPage: 0, totalPages: 320, dailyGoal: 20, status: "Lendo" },
    });
    const state = await createBookAction(initialCreateMutationState, createForm());
    expect(state.status).toBe("error");
    expect(state.submittedItemId).toBe(createId);
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("reading lifecycle actions", () => {
  it.each([
    { id: "another-book" },
    { currentPage: 12 },
    { totalPages: 500 },
  ])("não confirma atualização de outra leitura ou página", async (override) => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "reading-request-1", changed: true, book: book(override),
    });
    const result = await updateBookAction(initialInlineMutationState, updateForm());
    expect(result.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("não confirma exclusão de outro livro", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({
      operationId: "reading-request-1", id: "another-book", deleted: true,
    });
    const result = await deleteBookAction(initialInlineMutationState, updateForm({}));
    expect(result.status).toBe("error");
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it.each([createBookAction, updateBookAction, deleteBookAction])("exige autenticação antes do gate e do formulário", async (action) => {
    delete process.env.NEXO_WEB_WRITES_ENABLED;
    vi.mocked(requireAuthorizedSession).mockRejectedValue(new Error("Acesso não autorizado."));
    const get = vi.fn(() => { throw new Error("não ler"); });
    await expect(action(initialInlineMutationState as never, { get } as never)).rejects.toThrow("Acesso não autorizado.");
    expect(get).not.toHaveBeenCalled();
  });

  it("bloqueia o gate web antes de ler o formulário", async () => {
    delete process.env.NEXO_WEB_WRITES_ENABLED;
    const get = vi.fn(() => { throw new Error("não ler"); });
    const state = await updateBookAction(initialInlineMutationState, { get } as never);
    expect(get).not.toHaveBeenCalled();
    expect(state.message).toBe("As alterações ainda não estão disponíveis nesta versão.");
  });

  it("valida limite de página no servidor web", async () => {
    const state = await updateBookAction(initialInlineMutationState, updateForm({ currentPage: "321", totalPages: "320" }));
    expect(state).toEqual({ status: "error", message: "Revise os dados da leitura." });
    expect(requestNexoApi).not.toHaveBeenCalled();
  });

  it.each([
    [{ currentPage: "320", totalPages: "320" }, { currentPage: 320 }, book({ currentPage: 320, status: "Concluído" }), "Leitura concluída."],
    [{ status: "Concluído", totalPages: "320" }, { status: "Concluído" }, book({ currentPage: 320, status: "Concluído" }), "Leitura concluída."],
    [{ status: "Lendo", totalPages: "320" }, { status: "Lendo" }, book({ currentPage: 320, status: "Lendo" }), "Leitura reaberta."],
  ] as const)("confirma progresso, conclusão e reabertura", async (formValues, body, confirmed, message) => {
    vi.mocked(requestNexoApi).mockResolvedValue({ operationId: "reading-request-1", changed: true, book: confirmed });
    const state = await updateBookAction(initialInlineMutationState, updateForm(formValues));
    expect(requestNexoApi).toHaveBeenCalledWith("/v1/books/book-1", { method: "PATCH", body: JSON.stringify(body) }, UpdateBookResponseSchema);
    expect(state).toEqual({ status: "success", message });
    expect(revalidatePath.mock.calls).toEqual([["/leitura"], ["/"]]);
  });

  it("preserva mensagem segura em falha", async () => {
    vi.mocked(requestNexoApi).mockRejectedValue(new NexoApiError(503, "write_failed", "segredo"));
    const state = await updateBookAction(initialInlineMutationState, updateForm());
    expect(state).toEqual({ status: "error", message: "Não foi possível atualizar a leitura agora." });
  });

  it("confirma exclusão repetida e o ID da resposta", async () => {
    vi.mocked(requestNexoApi).mockResolvedValue({ operationId: "reading-request-1", id: "book-1", deleted: false });
    const form = updateForm({});
    const state = await deleteBookAction(initialInlineMutationState, form);
    expect(requestNexoApi).toHaveBeenCalledWith("/v1/books/book-1", { method: "DELETE" }, DeleteBookResponseSchema);
    expect(state.status).toBe("success");
    expect(revalidatePath.mock.calls).toEqual([["/leitura"], ["/"]]);
  });
});
