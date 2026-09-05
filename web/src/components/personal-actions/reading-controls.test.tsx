// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import type { InlineMutationState } from "@/actions/mutation-state";
import { ReadingControls, ReadingCreateForm } from "./reading-controls";

const { deleteBookAction, updateBookAction, createBookAction } = vi.hoisted(() => ({
  deleteBookAction: vi.fn(), updateBookAction: vi.fn(), createBookAction: vi.fn(),
}));
vi.mock("@/actions/reading", () => ({ deleteBookAction, updateBookAction, createBookAction }));

const book = {
  id: "book-1", title: "O Hobbit", author: "Tolkien", currentPage: 40,
  totalPages: 100, dailyTarget: 10, remainingTarget: 10,
  status: "Lendo", progress: 0.4, mutable: true,
};

function deferredState() {
  let resolve!: (state: InlineMutationState) => void;
  const promise = new Promise<InlineMutationState>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  deleteBookAction.mockReset();
  updateBookAction.mockReset();
  createBookAction.mockReset();
});

it("preserva a página digitada quando a API falha", async () => {
  updateBookAction.mockResolvedValue({ status: "error", message: "Não foi possível atualizar a leitura agora." });
  const user = userEvent.setup();
  render(<ReadingControls book={book} canMutate />);
  const page = screen.getByLabelText("Página atual");
  await user.clear(page);
  await user.type(page, "64");
  await user.click(screen.getByRole("button", { name: "Salvar leitura" }));
  expect(page).toHaveValue(64);
  expect(await screen.findByText("Não foi possível atualizar a leitura agora.")).toBeInTheDocument();
});

it("bloqueia botões durante envio e envia o estado desejado", async () => {
  const pending = deferredState();
  updateBookAction.mockReturnValueOnce(pending.promise);
  const user = userEvent.setup();
  render(<ReadingControls book={book} canMutate />);
  const conclude = screen.getByRole("button", { name: "Concluir" });
  await user.click(conclude);
  expect(conclude).toBeDisabled();
  const data = updateBookAction.mock.calls[0][1] as FormData;
  expect(Object.fromEntries(data)).toMatchObject({ id: "book-1", status: "Concluído", totalPages: "100" });
  pending.resolve({ status: "success", message: "Leitura concluída." });
  expect(await screen.findByText("Leitura concluída.")).toBeInTheDocument();
});

it("oferece reabertura para livro concluído", async () => {
  updateBookAction.mockResolvedValue({ status: "success", message: "Leitura reaberta." });
  const user = userEvent.setup();
  render(<ReadingControls book={{ ...book, currentPage: 100, status: "Concluído" }} canMutate />);
  await user.click(screen.getByRole("button", { name: "Voltar a ler" }));
  const data = updateBookAction.mock.calls[0][1] as FormData;
  expect(data.get("status")).toBe("Lendo");
});

it("exige confirmação contextual antes de excluir", async () => {
  deleteBookAction.mockResolvedValue({ status: "success", message: "Livro excluído." });
  const user = userEvent.setup();
  render(<ReadingControls book={book} canMutate />);
  await user.click(screen.getByRole("button", { name: "Excluir livro" }));
  expect(deleteBookAction).not.toHaveBeenCalled();
  expect(screen.getByText("Excluir O Hobbit?")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
  expect(deleteBookAction).toHaveBeenCalledOnce();
});

it.each([{ ...book, mutable: false }])("mantém livro legado sem controles", (legacy) => {
  render(<ReadingControls book={legacy} canMutate />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByText("Controles indisponíveis para este registro antigo.")).toBeInTheDocument();
});

it("esconde controles com gate fechado", () => {
  render(<ReadingControls book={book} canMutate={false} />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("preserva campos e identidade no erro e limpa apenas após confirmação", async () => {
  const id = "0f3ac9b0-5779-40ce-834d-40a8657684af";
  const next = "be23cdb7-f12d-45e8-bd42-8f5598a16651";
  createBookAction.mockResolvedValueOnce({
    status: "error", message: "Não foi possível salvar o livro agora.",
    fieldErrors: {}, submittedItemId: id, nextItemId: null,
  }).mockResolvedValueOnce({
    status: "success", message: "Livro adicionado.",
    fieldErrors: {}, submittedItemId: id, nextItemId: next,
  });
  const user = userEvent.setup();
  render(<ReadingCreateForm initialItemId={id} />);
  await user.type(screen.getByLabelText("Título"), "O Hobbit");
  await user.type(screen.getByLabelText("Autor"), "Tolkien");
  await user.type(screen.getByLabelText("Total de páginas"), "320");
  await user.type(screen.getByLabelText("Meta diária"), "20");
  await user.click(screen.getByRole("button", { name: "Adicionar livro" }));
  expect(await screen.findByText("Não foi possível salvar o livro agora.")).toBeInTheDocument();
  expect(screen.getByLabelText("Título")).toHaveValue("O Hobbit");
  expect(screen.getByLabelText("Meta diária")).toHaveValue(20);
  await user.click(screen.getByRole("button", { name: "Adicionar livro" }));
  expect(await screen.findByText("Livro adicionado.")).toBeInTheDocument();
  const attempts = createBookAction.mock.calls.map((call) => (call[1] as FormData).get("itemId"));
  expect(attempts).toEqual([id, id]);
  expect(screen.getByLabelText("Título")).toHaveValue("");
  expect(document.querySelector('input[name="itemId"]')).toHaveValue(next);
});
