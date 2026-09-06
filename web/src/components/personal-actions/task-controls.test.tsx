// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { InlineMutationState } from "@/actions/mutation-state";

import { TaskControls } from "./task-controls";

const { deleteTaskAction, setTaskCompletedAction } = vi.hoisted(() => ({
  deleteTaskAction: vi.fn(),
  setTaskCompletedAction: vi.fn(),
}));

vi.mock("@/actions/tasks", () => ({
  deleteTaskAction,
  setTaskCompletedAction,
}));

const task = {
  id: "task-1",
  title: "Revisar matemática",
  category: "Estudo",
  completed: false,
  mutable: true,
};

function deferredState() {
  let resolve!: (state: InlineMutationState) => void;
  const promise = new Promise<InlineMutationState>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  deleteTaskAction.mockReset();
  setTaskCompletedAction.mockReset();
});

describe("TaskControls", () => {
  it("bloqueia repetição enquanto a tarefa está sendo atualizada", async () => {
    const pending = deferredState();
    setTaskCompletedAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(<TaskControls task={task} canMutate />);
    const button = screen.getByRole("button", { name: "Concluir tarefa" });

    await user.click(button);

    expect(button).toBeDisabled();
    await user.click(button);
    expect(setTaskCompletedAction).toHaveBeenCalledTimes(1);
    const formData = setTaskCompletedAction.mock.calls[0][1] as FormData;
    expect(Object.fromEntries(formData)).toEqual({
      id: "task-1",
      completed: "true",
    });

    pending.resolve({ status: "success", message: "Tarefa concluída." });
    expect(await screen.findByText("Tarefa concluída.")).toBeInTheDocument();
  });

  it("reabre usando o estado desejado false", async () => {
    setTaskCompletedAction.mockResolvedValue({
      status: "success",
      message: "Tarefa reaberta.",
    });
    const user = userEvent.setup();
    render(<TaskControls task={{ ...task, completed: true }} canMutate />);

    await user.click(screen.getByRole("button", { name: "Reabrir tarefa" }));

    const formData = setTaskCompletedAction.mock.calls[0][1] as FormData;
    expect(formData.get("completed")).toBe("false");
    expect(await screen.findByText("Tarefa reaberta.")).toBeInTheDocument();
  });

  it("exige confirmação inline antes de excluir e bloqueia repetição", async () => {
    const pending = deferredState();
    deleteTaskAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(<TaskControls task={task} canMutate />);

    await user.click(screen.getByRole("button", { name: "Excluir tarefa" }));

    expect(deleteTaskAction).not.toHaveBeenCalled();
    const confirm = screen.getByRole("button", { name: "Confirmar exclusão" });
    const cancel = screen.getByRole("button", { name: "Cancelar exclusão" });
    expect(cancel).toBeVisible();

    await user.click(confirm);

    expect(confirm).toBeDisabled();
    expect(cancel).toBeDisabled();
    await user.click(confirm);
    expect(deleteTaskAction).toHaveBeenCalledTimes(1);
    const formData = deleteTaskAction.mock.calls[0][1] as FormData;
    expect(formData.get("id")).toBe("task-1");

    pending.resolve({ status: "success", message: "Tarefa excluída." });
    expect(await screen.findByText("Tarefa excluída.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Confirmar exclusão" }),
    ).not.toBeInTheDocument();
  });

  it("substitui erro antigo de exclusão pelo sucesso da ação mais recente", async () => {
    deleteTaskAction.mockResolvedValue({
      status: "error",
      message: "Não foi possível excluir a tarefa agora.",
    });
    setTaskCompletedAction.mockResolvedValue({
      status: "success",
      message: "Tarefa concluída.",
    });
    const user = userEvent.setup();
    render(<TaskControls task={task} canMutate />);

    await user.click(screen.getByRole("button", { name: "Excluir tarefa" }));
    await user.click(
      screen.getByRole("button", { name: "Confirmar exclusão" }),
    );
    expect(
      await screen.findByText("Não foi possível excluir a tarefa agora."),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Cancelar exclusão" }),
    );
    await user.click(screen.getByRole("button", { name: "Concluir tarefa" }));

    expect(await screen.findByText("Tarefa concluída.")).toBeInTheDocument();
    expect(
      screen.queryByText("Não foi possível excluir a tarefa agora."),
    ).not.toBeInTheDocument();
  });

  it("mantém a tarefa legada visível sem controles mutáveis", () => {
    render(
      <TaskControls
        task={{ ...task, id: "task-legacy-1", mutable: false }}
        canMutate
      />,
    );

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("não expõe controles quando o gate da página está fechado", () => {
    render(<TaskControls task={task} canMutate={false} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
