import { afterEach, describe, expect, it, vi } from "vitest";

import { requireAuthorizedSession } from "@/lib/auth-guard";

import { fetchNexoApi } from "./nexo-api";

const requireAuthorizedSessionMock = vi.mocked(requireAuthorizedSession);

afterEach(() => {
  requireAuthorizedSessionMock.mockReset();
  requireAuthorizedSessionMock.mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  } as never);
  delete process.env.NEXO_API_URL;
  delete process.env.NEXO_API_TOKEN;
  vi.unstubAllGlobals();
});

describe("fetchNexoApi", () => {
  it("revalida a sessão antes mesmo de decidir pelo fallback local", async () => {
    requireAuthorizedSessionMock.mockRejectedValue(
      new Error("Acesso não autorizado."),
    );
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchNexoApi("/v1/dashboard/today")).rejects.toThrow(
      "Acesso não autorizado.",
    );
    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("mantém o fallback sem API para uma sessão autorizada", async () => {
    await expect(fetchNexoApi("/v1/dashboard/today")).resolves.toBeNull();
    expect(requireAuthorizedSessionMock).toHaveBeenCalledOnce();
  });
});
