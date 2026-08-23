import { describe, expect, it } from "vitest";

import { isAllowedGitHubIdentity } from "./auth-policy";

describe("isAllowedGitHubIdentity", () => {
  it("autoriza somente o ID numérico configurado", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "12345", githubLogin: "DaviFreitas-dev" },
        "12345",
      ),
    ).toBe(true);
  });

  it("recusa o mesmo login com outro ID", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "99999", githubLogin: "DaviFreitas-dev" },
        "12345",
      ),
    ).toBe(false);
  });

  it("falha fechado sem ID configurado", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "12345", githubLogin: "DaviFreitas-dev" },
        undefined,
      ),
    ).toBe(false);
  });

  it("recusa uma configuração que não seja um ID numérico", () => {
    expect(
      isAllowedGitHubIdentity(
        { githubId: "DaviFreitas-dev", githubLogin: "DaviFreitas-dev" },
        "DaviFreitas-dev",
      ),
    ).toBe(false);
  });
});
