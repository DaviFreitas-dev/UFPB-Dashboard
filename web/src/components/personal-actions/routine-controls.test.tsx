// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  CreateMutationState,
  InlineMutationState,
} from "@/actions/mutation-state";

import { RoutineControls, RoutineCreateForm } from "./routine-controls";

const {
  createRoutineItemAction,
  deleteRoutineItemAction,
  setRoutineItemCompletedAction,
} = vi.hoisted(() => ({
  createRoutineItemAction: vi.fn(),
  deleteRoutineItemAction: vi.fn(),
  setRoutineItemCompletedAction: vi.fn(),
}));

vi.mock("@/actions/routine", () => ({
  createRoutineItemAction,
  deleteRoutineItemAction,
  setRoutineItemCompletedAction,
}));

const item = {
  id: "custom:routine-1",
  sourceId: "routine-1",
  time: "08:30",
  title: "Dentista",
  category: "Avulso",
  kind: "custom" as const,
  completed: false,
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
  createRoutineItemAction.mockReset();
  deleteRoutineItemAction.mockReset();
  setRoutineItemCompletedAction.mockReset();
});

describe("RoutineControls", () => {
  it("envia sourceId e o estado desejado, bloqueando repetição", async () => {
    const pending = deferredState<InlineMutationState>();
    setRoutineItemCompletedAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(<RoutineControls item={item} canMutate />);
    const button = screen.getByRole("button", {
      name: "Concluir compromisso",
    });

    await user.click(button);

    expect(button).toBeDisabled();
    await user.click(button);
    expect(setRoutineItemCompletedAction).toHaveBeenCalledTimes(1);
    const formData = setRoutineItemCompletedAction.mock.calls[0][1] as FormData;
    expect(Object.fromEntries(formData)).toEqual({
      id: "routine-1",
      completed: "true",
    });

    pending.resolve({ status: "success", message: "Compromisso concluído." });
    expect(await screen.findByText("Compromisso concluído.")).toBeInTheDocument();
  });

  it("reabre usando completed=false", async () => {
    setRoutineItemCompletedAction.mockResolvedValue({
      status: "success",
      message: "Compromisso reaberto.",
    });
    const user = userEvent.setup();
    render(<RoutineControls item={{ ...item, completed: true }} canMutate />);

    await user.click(
      screen.getByRole("button", { name: "Reabrir compromisso" }),
    );

    const formData = setRoutineItemCompletedAction.mock.calls[0][1] as FormData;
    expect(formData.get("completed")).toBe("false");
  });

  it("exige confirmação antes de excluir", async () => {
    deleteRoutineItemAction.mockResolvedValue({
      status: "success",
      message: "Compromisso excluído.",
    });
    const user = userEvent.setup();
    render(<RoutineControls item={item} canMutate />);

    await user.click(
      screen.getByRole("button", { name: "Excluir compromisso" }),
    );
    expect(deleteRoutineItemAction).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Confirmar exclusão" }),
    );

    const formData = deleteRoutineItemAction.mock.calls[0][1] as FormData;
    expect(formData.get("id")).toBe("routine-1");
    expect(await screen.findByText("Compromisso excluído.")).toBeInTheDocument();
  });

  it("não oferece check-in para um item da semana fixa", () => {
    render(
      <RoutineControls
        item={{
          ...item,
          id: "fixed:weekly-1",
          sourceId: "",
          kind: "fixed",
          mutable: false,
        }}
        canMutate
      />,
    );

    expect(
      screen.queryByRole("button", { name: /concluir/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Check-in disponível na próxima etapa."),
    ).toBeInTheDocument();
  });

  it("mantém legado visível sem controle mutável", () => {
    render(
      <RoutineControls
        item={{ ...item, sourceId: "", mutable: false }}
        canMutate
      />,
    );

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(
      screen.getByText("Disponível após a atualização dos dados."),
    ).toBeInTheDocument();
  });

  it("não expõe controles ou avisos por item com gate fechado", () => {
    const { container } = render(
      <RoutineControls item={item} canMutate={false} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe("RoutineCreateForm", () => {
  it("preserva valores e UUID durante uma falha", async () => {
    const pending = deferredState<CreateMutationState>();
    createRoutineItemAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(
      <RoutineCreateForm
        initialItemId="0f3ac9b0-5779-40ce-834d-40a8657684af"
        selectedDate="2026-08-25"
      />,
    );
    const activity = screen.getByLabelText("Atividade");
    const time = screen.getByLabelText("Horário");

    await user.type(activity, "Dentista");
    await user.type(time, "08:30");
    await user.click(
      screen.getByRole("button", { name: "Adicionar compromisso" }),
    );

    pending.resolve({
      status: "error",
      message: "Não foi possível adicionar o compromisso agora.",
      fieldErrors: {},
      submittedItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
      nextItemId: null,
    });
    expect(
      await screen.findByText("Não foi possível adicionar o compromisso agora."),
    ).toBeInTheDocument();
    expect(activity).toHaveValue("Dentista");
    expect(time).toHaveValue("08:30");
    const formData = createRoutineItemAction.mock.calls[0][1] as FormData;
    expect(formData.get("itemId")).toBe(
      "0f3ac9b0-5779-40ce-834d-40a8657684af",
    );
    expect(formData.get("date")).toBe("2026-08-25");
  });

  it("bloqueia o formulário enquanto envia", async () => {
    const pending = deferredState<CreateMutationState>();
    createRoutineItemAction.mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(
      <RoutineCreateForm
        initialItemId="0f3ac9b0-5779-40ce-834d-40a8657684af"
        selectedDate="2026-08-25"
      />,
    );
    await user.type(screen.getByLabelText("Atividade"), "Dentista");
    await user.type(screen.getByLabelText("Horário"), "08:30");
    const submit = screen.getByRole("button", {
      name: "Adicionar compromisso",
    });

    await user.click(submit);

    expect(screen.getByRole("button", { name: "Salvando..." })).toBeDisabled();
    expect(screen.getByLabelText("Atividade")).toBeDisabled();
  });
});
