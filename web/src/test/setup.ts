import { AsyncLocalStorage } from "node:async_hooks";

import { vi } from "vitest";

Object.assign(globalThis, { AsyncLocalStorage });

vi.mock("@/lib/auth-guard", () => ({
  requireAuthorizedSession: vi.fn().mockResolvedValue({
    user: { githubId: "test-user", githubLogin: "DaviFreitas-dev" },
  }),
}));
