// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import type { CreateMutationState } from "@/actions/mutation-state";
import { ActivityCreateForm } from "./activity-controls";

const { registerActivityAction } = vi.hoisted(() => ({ registerActivityAction: vi.fn() }));
vi.mock("@/actions/activity", () => ({ registerActivityAction }));

it("preserva tipo, data e UUID após falha, bloqueia envio e renova só no sucesso", async () => {
  const id = "fe55a71b-ab60-4bde-98cc-9bc487a7a4a4";
  const next = "592be4c5-78d9-4a38-8907-66078c8e7635";
  let resolve!: (state: CreateMutationState) => void;
  registerActivityAction.mockReturnValueOnce(new Promise<CreateMutationState>((done) => { resolve = done; }));
  const user = userEvent.setup();
  render(<ActivityCreateForm initialItemId={id} selectedDate="2026-08-25" />);
  await user.selectOptions(screen.getByLabelText("Atividade realizada"), "Corrida");
  expect(screen.getByLabelText("Atividade realizada")).toHaveValue("Corrida");
  await user.click(screen.getByRole("button", { name: "Registrar atividade" }));
  expect(screen.getByRole("button", { name: "Registrando..." })).toBeDisabled();
  expect((registerActivityAction.mock.calls[0][1] as FormData).get("type")).toBe("Corrida");
  resolve({ status: "error", message: "Não foi possível registrar a atividade agora.",
    fieldErrors: {}, submittedItemId: id, nextItemId: null });
  expect(await screen.findByText("Não foi possível registrar a atividade agora.")).toBeInTheDocument();
  expect(screen.getByLabelText("Atividade realizada")).toHaveValue("Corrida");
  expect(screen.getByLabelText("Data")).toHaveValue("2026-08-25");
  registerActivityAction.mockResolvedValueOnce({ status: "success", message: "Atividade registrada.",
    fieldErrors: {}, submittedItemId: id, nextItemId: next });
  await user.click(screen.getByRole("button", { name: "Registrar atividade" }));
  expect(await screen.findByText("Atividade registrada.")).toBeInTheDocument();
  expect(registerActivityAction.mock.calls.map((call) => (call[1] as FormData).get("itemId"))).toEqual([id, id]);
  expect(document.querySelector('input[name="itemId"]')).toHaveValue(next);
});
