// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  CreateMutationState,
  InlineMutationState,
} from "@/actions/mutation-state";

import { HabitControls, HabitCreateForm } from "./habit-controls";

const {
  createHabitAction,
  setHabitActiveAction,
  setHabitCompletedAction,
} = vi.hoisted(() => ({
  createHabitAction: vi.fn(),
  setHabitActiveAction: vi.fn(),
  setHabitCompletedAction: vi.fn(),
}));

vi.mock("@/actions/habits", () => ({
  createHabitAction,
  setHabitActiveAction,
  setHabitCompletedAction,
}));

const habit = {
  configId: "habit-config-1",
  logId: null,
  title: "Ler",
  completed: false,
  streakDays: 3,
  mutable: true,
};

function deferredState<T>() {
  let resolve!: (state: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  createHabitAction.mockReset();
  setHabitActiveAction.mockReset();
  setHabitCompletedAction.mockReset();
});

describe("HabitControls", () => {
  it("marca pelo configId e data, bloqueando envio duplo", async () => {
    const pending = deferredState<InlineMutationState>();
    setHabitCompletedAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(
      <HabitControls
        canMutate
        date="2026-08-25"
        habit={habit}
      />,
    );
    const button = screen.getByRole("button", { name: "Marcar como feito" });

    await user.click(button);
    expect(button).toBeDisabled();
    await user.click(button);

    expect(setHabitCompletedAction).toHaveBeenCalledTimes(1);
    const formData = setHabitCompletedAction.mock.calls[0][1] as FormData;
    expect(Object.fromEntries(formData)).toEqual({
      configId: "habit-config-1",
      date: "2026-08-25",
      completed: "true",
    });
    expect(formData.has("logId")).toBe(false);

    pending.resolve({ status: "success", message: "Hábito marcado como feito." });
    expect(await screen.findByText("Hábito marcado como feito.")).toBeInTheDocument();
  });

  it("desmarca com completed=false", async () => {
    setHabitCompletedAction.mockResolvedValue({
      status: "success",
      message: "Hábito desmarcado.",
    });
    const user = userEvent.setup();
    render(
      <HabitControls
        canMutate
        date="2026-08-25"
        habit={{ ...habit, completed: true, logId: "habit-log-1" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Desmarcar" }));

    const formData = setHabitCompletedAction.mock.calls[0][1] as FormData;
    expect(formData.get("completed")).toBe("false");
  });

  it("exige confirmação inline antes de arquivar", async () => {
    setHabitActiveAction.mockResolvedValue({
      status: "success",
      message: "Hábito arquivado.",
    });
    const user = userEvent.setup();
    render(<HabitControls canMutate date="2026-08-25" habit={habit} />);

    await user.click(screen.getByRole("button", { name: "Arquivar hábito" }));
    expect(setHabitActiveAction).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Confirmar arquivo" }));

    const formData = setHabitActiveAction.mock.calls[0][1] as FormData;
    expect(Object.fromEntries(formData)).toEqual({
      configId: "habit-config-1",
      active: "false",
    });
    expect(await screen.findByText("Hábito arquivado.")).toBeInTheDocument();
  });

  it("mantém legado visível com explicação curta", () => {
    render(
      <HabitControls
        canMutate
        date="2026-08-25"
        habit={{ ...habit, configId: "", mutable: false }}
      />,
    );

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(
      screen.getByText("Disponível após a atualização dos dados."),
    ).toBeInTheDocument();
  });

  it("não mostra controles ou aviso por item com gate fechado", () => {
    const { container } = render(
      <HabitControls canMutate={false} date="2026-08-25" habit={habit} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe("HabitCreateForm", () => {
  it("preserva o nome e UUID em falha", async () => {
    const pending = deferredState<CreateMutationState>();
    createHabitAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(
      <HabitCreateForm initialItemId="398615a3-c08d-4f42-a9f4-b5d5c5c94515" />,
    );
    const name = screen.getByLabelText("Nome do hábito");

    await user.type(name, "Meditar");
    await user.click(screen.getByRole("button", { name: "Adicionar hábito" }));

    expect(screen.getByRole("button", { name: "Salvando..." })).toBeDisabled();
    expect(name).toBeDisabled();
    pending.resolve({
      status: "error",
      message: "Não foi possível adicionar o hábito agora.",
      fieldErrors: {},
      submittedItemId: "398615a3-c08d-4f42-a9f4-b5d5c5c94515",
      nextItemId: null,
    });

    expect(await screen.findByText("Não foi possível adicionar o hábito agora.")).toBeInTheDocument();
    expect(name).toHaveValue("Meditar");
  });

  it("limpa o nome apenas depois de sucesso", async () => {
    createHabitAction.mockResolvedValue({
      status: "success",
      message: "Hábito criado.",
      fieldErrors: {},
      submittedItemId: "398615a3-c08d-4f42-a9f4-b5d5c5c94515",
      nextItemId: "4fd1bf89-bc5f-43da-bf85-79c49b78a8e0",
    });
    const user = userEvent.setup();
    render(
      <HabitCreateForm initialItemId="398615a3-c08d-4f42-a9f4-b5d5c5c94515" />,
    );

    await user.type(screen.getByLabelText("Nome do hábito"), "Meditar");
    await user.click(screen.getByRole("button", { name: "Adicionar hábito" }));

    expect(await screen.findByText("Hábito criado.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome do hábito")).toHaveValue("");
  });
});
