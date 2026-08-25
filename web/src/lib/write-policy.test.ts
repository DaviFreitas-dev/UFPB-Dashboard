import { afterEach, describe, expect, it } from "vitest";

import { mutationsUiEnabled } from "./write-policy";

afterEach(() => {
  delete process.env.NEXO_WEB_WRITES_ENABLED;
});

describe("mutationsUiEnabled", () => {
  it("fica desativado por padrão", () => {
    expect(mutationsUiEnabled()).toBe(false);
  });

  it("aceita somente true explícito", () => {
    for (const disabledValue of ["1", "yes", "enabled", "false"]) {
      process.env.NEXO_WEB_WRITES_ENABLED = disabledValue;
      expect(mutationsUiEnabled()).toBe(false);
    }

    process.env.NEXO_WEB_WRITES_ENABLED = " TRUE ";
    expect(mutationsUiEnabled()).toBe(true);
  });
});
