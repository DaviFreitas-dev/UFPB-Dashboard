// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { createDemoDashboard } from "@/lib/demo-dashboard";
import { TodayDashboard } from "./today-dashboard";

const actions = vi.hoisted(() => ({
  setTaskCompletedAction: vi.fn(), deleteTaskAction: vi.fn(), createTaskAction: vi.fn(),
  setRoutineItemCompletedAction: vi.fn(), deleteRoutineItemAction: vi.fn(), createRoutineItemAction: vi.fn(),
  setHabitCompletedAction: vi.fn(), setHabitActiveAction: vi.fn(), createHabitAction: vi.fn(),
  updateBookAction: vi.fn(), deleteBookAction: vi.fn(), createBookAction: vi.fn(),
  registerActivityAction: vi.fn(),
}));
vi.mock("@/actions/tasks", () => actions);
vi.mock("@/actions/routine", () => actions);
vi.mock("@/actions/habits", () => actions);
vi.mock("@/actions/reading", () => actions);
vi.mock("@/actions/activity", () => actions);

const taskId = "b6366767-8490-4b24-a306-79cfb57eae61";
const activityId = "952af671-f94b-4e4c-a91d-65899b3a3c0e";
function dashboard() {
  const demo = createDemoDashboard(new Date("2026-08-25T12:00:00"));
  return { ...demo,
    priorities: [
      { id: "task-real", title: "Prioridade real", category: "Estudo", completed: false, mutable: true },
      { id: "legacy-task", title: "Tarefa antiga", category: "Outro", completed: false, mutable: false },
    ],
    agenda: [
      { id: "same", sourceId: "weekly-1", title: "Aula fixa", time: "08:00", category: "Agenda", kind: "fixed" as const, completed: false, mutable: false },
      { id: "same", sourceId: "routine-1", title: "Rotina real", time: "09:00", category: "Rotina", kind: "custom" as const, completed: false, mutable: true },
    ],
    habits: [{ configId: "habit-1", logId: null, title: "Ler", completed: false, streakDays: 0, mutable: true }],
    reading: { id: "book-1", title: "Livro real", author: "", currentPage: 20, totalPages: 100, dailyTarget: 10, mutable: true },
  };
}
beforeEach(() => Object.values(actions).forEach((action) => action.mockReset()));

it("reutiliza ações pessoais sem permitir escrita na agenda semanal ou linha sem ID", async () => {
  actions.setTaskCompletedAction.mockResolvedValue({ status: "success", message: "Tarefa concluída." });
  actions.setRoutineItemCompletedAction.mockResolvedValue({ status: "success", message: "Compromisso concluído." });
  actions.setHabitCompletedAction.mockResolvedValue({ status: "success", message: "Hábito registrado." });
  const user = userEvent.setup();
  render(<TodayDashboard dashboard={dashboard()} source="api" canMutate />);
  const task = screen.getByRole("group", { name: "Prioridade real" });
  expect(within(screen.getByRole("group", { name: "Tarefa antiga" })).queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByText("Agenda fixa")).toBeInTheDocument();
  expect(within(screen.getByRole("group", { name: "Aula fixa" })).queryByRole("button")).not.toBeInTheDocument();
  await user.click(within(task).getByRole("button", { name: "Concluir tarefa" }));
  expect((actions.setTaskCompletedAction.mock.calls[0][1] as FormData).get("id")).toBe("task-real");
  await user.click(within(screen.getByRole("group", { name: "Rotina real" })).getByRole("button", { name: "Concluir compromisso" }));
  expect((actions.setRoutineItemCompletedAction.mock.calls[0][1] as FormData).get("id")).toBe("routine-1");
  await user.click(within(screen.getByRole("group", { name: "Ler" })).getByRole("button", { name: "Marcar como feito" }));
  expect(Object.fromEntries(actions.setHabitCompletedAction.mock.calls[0][1] as FormData))
    .toMatchObject({ configId: "habit-1", date: "2026-08-25", completed: "true" });
  expect(screen.queryByRole("button", { name: "Excluir tarefa" })).not.toBeInTheDocument();
});

it.each([{ source: "api" as const, canMutate: false }, { source: "demo" as const, canMutate: true }])(
  "não mostra mutações com gate fechado ou demonstração", (props) => {
    render(<TodayDashboard {...props} dashboard={dashboard()} initialTaskId={taskId} initialActivityId={activityId} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getAllByText("Alterações indisponíveis nesta versão.")).toHaveLength(1);
  },
);

it("mantém falha de leitura visível e compartilha IDs estáveis dos formulários", async () => {
  actions.updateBookAction.mockResolvedValue({ status: "error", message: "Não foi possível atualizar a leitura agora." });
  actions.registerActivityAction.mockResolvedValue({ status: "error", message: "Não foi possível registrar a atividade agora.",
    fieldErrors: {}, submittedItemId: activityId, nextItemId: null });
  const user = userEvent.setup();
  const { container } = render(<TodayDashboard dashboard={dashboard()} source="api" canMutate
    initialTaskId={taskId} initialActivityId={activityId} />);
  await user.clear(screen.getByLabelText("Página atual"));
  await user.type(screen.getByLabelText("Página atual"), "30");
  await user.click(screen.getByRole("button", { name: "Salvar leitura" }));
  expect(await screen.findByText("Não foi possível atualizar a leitura agora.")).toBeInTheDocument();
  expect(screen.getByLabelText("Página atual")).toHaveValue(30);
  await user.click(screen.getByText("Registrar atividade", { selector: "summary" }));
  await user.click(screen.getByRole("button", { name: "Registrar atividade" }));
  expect(await screen.findByText("Não foi possível registrar a atividade agora.")).toBeInTheDocument();
  expect((actions.registerActivityAction.mock.calls[0][1] as FormData).get("itemId")).toBe(activityId);
  expect(Array.from(container.querySelectorAll('input[name="itemId"]'), (input) => (input as HTMLInputElement).value))
    .toEqual([taskId, activityId]);
  const ids = Array.from(container.querySelectorAll("[id]"), (item) => item.id);
  expect(new Set(ids).size).toBe(ids.length);
});
