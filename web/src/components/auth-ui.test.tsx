import {
  Children,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
import { describe, expect, it, vi } from "vitest";

const { signInMock, signOutMock } = vi.hoisted(() => ({
  signInMock: vi.fn(),
  signOutMock: vi.fn(),
}));

vi.mock("@/auth", () => ({
  signIn: signInMock,
  signOut: signOutMock,
}));

import AccessDeniedPage from "@/app/acesso-negado/page";
import SignInPage from "@/app/entrar/page";
import { AppShell } from "./app-shell";

type ElementWithProps = ReactElement<Record<string, unknown>>;

function findElement(
  node: ReactNode,
  predicate: (element: ElementWithProps) => boolean,
): ElementWithProps | undefined {
  if (!isValidElement<Record<string, unknown>>(node)) {
    return undefined;
  }
  if (predicate(node)) {
    return node;
  }
  for (const child of Children.toArray(node.props.children as ReactNode)) {
    const match = findElement(child, predicate);
    if (match) {
      return match;
    }
  }
  return undefined;
}

function textContent(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (!isValidElement<Record<string, unknown>>(node)) {
    return "";
  }
  return Children.toArray(node.props.children as ReactNode)
    .map(textContent)
    .join(" ");
}

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

describe("interface de autenticação", () => {
  it("entra com GitHub e retorna ao produto", async () => {
    const page = SignInPage();
    const form = findElement(page, (element) => element.type === "form");

    expect(textContent(page)).toContain("Acesso pessoal");
    expect(textContent(page)).toContain("Entrar com GitHub");
    expect(typeof form?.props.action).toBe("function");
    const action = form?.props.action as () => Promise<void>;
    await expect(action()).resolves.toBeUndefined();
    expect(signInMock).toHaveBeenCalledWith("github", { redirectTo: "/" });
  });

  it("explica a recusa e permite voltar ao login", () => {
    const page = AccessDeniedPage();

    expect(textContent(page)).toContain("Acesso não autorizado");
    const link = findElement(
      page,
      (element) =>
        element.type !== "form" && element.props.href === "/entrar",
    );
    expect(link?.props.href).toBe("/entrar");
  });

  it("encerra a sessão pelo shell protegido", async () => {
    const shell = AppShell({
      children: <p>Conteúdo protegido</p>,
      currentPath: "/",
      user: {
        level: 4,
        xp: 3420,
        xpInLevel: 420,
        xpPerLevel: 1000,
        xpToNextLevel: 580,
        streakDays: 6,
        longestStreak: 14,
      },
    });
    const forms = findElements(
      shell,
      (element) =>
        element.type === "form" && textContent(element).includes("Sair"),
    );

    expect(forms).toHaveLength(2);
    for (const form of forms) {
      expect(typeof form.props.action).toBe("function");
      const action = form.props.action as () => Promise<void>;
      await expect(action()).resolves.toBeUndefined();
    }
    expect(signOutMock).toHaveBeenCalledTimes(2);
    expect(signOutMock).toHaveBeenCalledWith({ redirectTo: "/entrar" });
  });
});
