import { describe, expect, it } from "vitest";

import { createDemoProfileWorkspace } from "./demo-profile-workspace";
import { achievementFootnote, isProfileWorkspace } from "./profile-workspace";

describe("isProfileWorkspace", () => {
  it("aceita o contrato completo de perfil", () => {
    expect(isProfileWorkspace(createDemoProfileWorkspace(new Date(2026, 7, 22)))).toBe(true);
  });

  it("recusa conquistas e configurações incompletas vindas da API", () => {
    const workspace = createDemoProfileWorkspace(new Date(2026, 7, 22));

    expect(
      isProfileWorkspace({
        ...workspace,
        achievements: { ...workspace.achievements, unlocked: "3" },
      }),
    ).toBe(false);
    expect(
      isProfileWorkspace({
        ...workspace,
        settings: {
          ...workspace.settings,
          subjects: [{ discipline: "Física", hours: 3 }],
        },
      }),
    ).toBe(false);
  });
});

describe("achievementFootnote", () => {
  it("não contradiz uma conquista calculada antes de a data ser salva", () => {
    expect(
      achievementFootnote({
        id: "1",
        title: "Primeiro passo",
        description: "Conclua sua primeira hora de estudo.",
        unlocked: true,
        unlockedAt: null,
      }),
    ).toBe("Concluída recentemente.");
  });
});
