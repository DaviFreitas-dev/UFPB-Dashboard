import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TasksPage from "@/app/tarefas/page";
import { createDemoPersonalWorkspace } from "@/lib/demo-personal-workspace";
import type { PersonalWorkspaceResult } from "@/lib/personal-workspace";

import {
  resolveItemIdAfterAction,
  TaskCreateForm,
} from "./task-create-form";
import { TasksWorkspace } from "./tasks-workspace";

const { loadPersonalWorkspace } = vi.hoisted(() => ({
  loadPersonalWorkspace: vi.fn(),
}));

vi.mock("@/lib/personal-workspace-source", () => ({ loadPersonalWorkspace }));

type ElementWithProps = ReactElement<Record<string, unknown>>;

function findElements(
  node: ReactNode,
  predicate: (element: ElementWithProps) => boolean,
): ElementWithProps[] {
  if (!isValidElement<Record<string, unknown>>(node)) {
    return [];
  }
  const matches = predicate(node) ? [node] : [];
  return Children.toArray(node.props.children as ReactNode).reduce<
    ElementWithProps[]
  >(
    (all, child) => all.concat(findElements(child, predicate)),
    matches,
  );
}

function workspaceResult(source: "api" | "demo"): PersonalWorkspaceResult {
  return {
    source,
    workspace: createDemoPersonalWorkspace(new Date("2026-08-23T12:00:00")),
  };
}

beforeEach(() => {
  loadPersonalWorkspace.mockReset();
  delete process.env.NEXO_WEB_WRITES_ENABLED;
  delete process.env.NEXO_API_TOKEN;
});

afterEach(() => {
  delete process.env.NEXO_WEB_WRITES_ENABLED;
  delete process.env.NEXO_API_TOKEN;
});

describe("gate do formulário de tarefas", () => {
  it("não renderiza controles de escrita quando o gate está desligado", () => {
    const result = workspaceResult("api");
    const tree = TasksWorkspace({
      ...result,
      canMutate: false,
      initialItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
    });

    expect(
      findElements(tree, (element) => element.type === TaskCreateForm),
    ).toHaveLength(0);
  });

  it("renderiza o formulário somente quando a página autoriza mutações", () => {
    const result = workspaceResult("api");
    const tree = TasksWorkspace({
      ...result,
      canMutate: true,
      initialItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
    });
    const forms = findElements(
      tree,
      (element) => element.type === TaskCreateForm,
    );

    expect(forms).toHaveLength(1);
    expect(forms[0].props).toMatchObject({
      initialItemId: "0f3ac9b0-5779-40ce-834d-40a8657684af",
      selectedDate: "2026-08-23",
    });
  });

  it("mantém o gate fechado na página sem flag ou sem fonte real", async () => {
    loadPersonalWorkspace.mockResolvedValueOnce(workspaceResult("api"));
    const withoutFlag = await TasksPage({ searchParams: Promise.resolve({}) });
    const disabledWorkspace = findElements(
      withoutFlag,
      (element) => element.type === TasksWorkspace,
    )[0];

    process.env.NEXO_WEB_WRITES_ENABLED = "true";
    loadPersonalWorkspace.mockResolvedValueOnce(workspaceResult("demo"));
    const demo = await TasksPage({ searchParams: Promise.resolve({}) });
    const demoWorkspace = findElements(
      demo,
      (element) => element.type === TasksWorkspace,
    )[0];

    expect(disabledWorkspace.props.canMutate).toBe(false);
    expect(demoWorkspace.props.canMutate).toBe(false);
  });

  it("abre o gate na página apenas com flag explícita e fonte real", async () => {
    process.env.NEXO_WEB_WRITES_ENABLED = "true";
    loadPersonalWorkspace.mockResolvedValue(workspaceResult("api"));

    const page = await TasksPage({ searchParams: Promise.resolve({}) });
    const workspace = findElements(
      page,
      (element) => element.type === TasksWorkspace,
    )[0];

    expect(workspace.props.canMutate).toBe(true);
    expect(workspace.props.initialItemId).toMatch(/^[0-9a-f-]{36}$/);
  });
});

describe("formulário de criação de tarefa", () => {
  it("preserva o ID após erro e só gira depois do sucesso confirmado", () => {
    const current = "0f3ac9b0-5779-40ce-834d-40a8657684af";
    const next = "b6f79644-8787-40a7-8d5d-4f83078657ab";

    expect(
      resolveItemIdAfterAction(current, {
        status: "error",
        message: "Falhou.",
        fieldErrors: {},
        submittedItemId: current,
        nextItemId: null,
      }),
    ).toBe(current);
    expect(
      resolveItemIdAfterAction(current, {
        status: "success",
        message: "Tarefa adicionada.",
        fieldErrors: {},
        submittedItemId: current,
        nextItemId: next,
      }),
    ).toBe(next);
  });

  it("gera HTML acessível sem expor o token do servidor", () => {
    process.env.NEXO_API_TOKEN = "segredo-que-nao-pode-aparecer";

    const html = renderToStaticMarkup(
      <TaskCreateForm
        initialItemId="0f3ac9b0-5779-40ce-834d-40a8657684af"
        selectedDate="2026-08-23"
      />,
    );

    expect(html).toContain("Nova tarefa");
    expect(html).toContain("O que precisa ser feito?");
    expect(html).toContain("Categoria");
    expect(html).toContain("Adicionar tarefa");
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain('name="itemId"');
    expect(html).toContain("0f3ac9b0-5779-40ce-834d-40a8657684af");
    expect(html).not.toContain("segredo-que-nao-pode-aparecer");
    expect(html).not.toContain("NEXO_API_TOKEN");
  });
});
