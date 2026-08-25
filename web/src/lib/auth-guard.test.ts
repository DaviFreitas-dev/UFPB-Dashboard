import { afterEach, describe, expect, it, vi } from "vitest";

const authMock = vi.hoisted(() => vi.fn());

vi.unmock("@/lib/auth-guard");
vi.mock("@/auth", () => ({ auth: authMock }));

import { requireAuthorizedSession } from "./auth-guard";

afterEach(() => {
  authMock.mockReset();
  delete process.env.NEXO_ALLOWED_GITHUB_ID;
});

describe("requireAuthorizedSession", () => {
  it("devolve a sessão cujo GitHub ID está autorizado", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";
    const session = {
      user: { githubId: "12345", githubLogin: "DaviFreitas-dev" },
    };
    authMock.mockResolvedValue(session);

    await expect(requireAuthorizedSession()).resolves.toBe(session);
  });

  it("recusa uma sessão com o mesmo login e outro ID", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";
    authMock.mockResolvedValue({
      user: { githubId: "99999", githubLogin: "DaviFreitas-dev" },
    });

    await expect(requireAuthorizedSession()).rejects.toThrow(
      "Acesso não autorizado.",
    );
  });

  it("recusa quando não há sessão", async () => {
    process.env.NEXO_ALLOWED_GITHUB_ID = "12345";
    authMock.mockResolvedValue(null);

    await expect(requireAuthorizedSession()).rejects.toThrow(
      "Acesso não autorizado.",
    );
  });

  it("falha fechado quando a allowlist está ausente", async () => {
    authMock.mockResolvedValue({
      user: { githubId: "12345", githubLogin: "DaviFreitas-dev" },
    });

    await expect(requireAuthorizedSession()).rejects.toThrow(
      "Acesso não autorizado.",
    );
  });
});
