import { afterEach, describe, expect, it } from "vitest";

import { authConfig } from "@/auth";

type AuthCallbacks = NonNullable<typeof authConfig.callbacks>;

const callbacks = authConfig.callbacks as AuthCallbacks;

afterEach(() => {
  delete process.env.NEXO_ALLOWED_GITHUB_ID;
});

describe("Auth.js", () => {
  it("usa JWT e as páginas públicas de entrada e recusa", () => {
    expect(authConfig.session?.strategy).toBe("jwt");
    expect(authConfig.pages).toMatchObject({
      error: "/acesso-negado",
      signIn: "/entrar",
    });
  });

  it("permite o GitHub ID configurado", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";

    expect(
      await callbacks.signIn?.({
        account: { providerAccountId: "12345" },
        profile: { id: 12345, login: "DaviFreitas-dev" },
      } as never),
    ).toBe(true);
  });

  it("recusa o mesmo login quando o ID imutável diverge", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";

    expect(
      await callbacks.signIn?.({
        account: { providerAccountId: "99999" },
        profile: { id: 99999, login: "DaviFreitas-dev" },
      } as never),
    ).toBe(false);
  });

  it("recusa login quando a allowlist está ausente", async () => {
    expect(
      await callbacks.signIn?.({
        account: { providerAccountId: "12345" },
        profile: { id: 12345, login: "DaviFreitas-dev" },
      } as never),
    ).toBe(false);
  });

  it("propaga ID e login do JWT para a sessão", async () => {
    const token = await callbacks.jwt?.({
      account: { providerAccountId: "12345" },
      profile: { id: 12345, login: "DaviFreitas-dev" },
      token: {},
    } as never);
    const session = await callbacks.session?.({
      session: { user: {} },
      token,
    } as never);

    expect(session?.user).toMatchObject({
      githubId: "12345",
      githubLogin: "DaviFreitas-dev",
    });
  });

  it("revalida a allowlist ao autorizar uma sessão", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";

    expect(
      await callbacks.authorized?.({
        auth: {
          user: { githubId: "99999", githubLogin: "DaviFreitas-dev" },
        },
      } as never),
    ).toBe(false);
  });
});
