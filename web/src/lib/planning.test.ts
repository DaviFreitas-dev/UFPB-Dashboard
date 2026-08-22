import { describe, expect, it } from "vitest";

import { createDemoPlanning } from "./demo-planning";
import { isPlanningDashboard } from "./planning";

describe("planning contract", () => {
  it("gera a semana de segunda a domingo mesmo quando a referência é domingo", () => {
    const planning = createDemoPlanning(new Date(2026, 7, 23));

    expect(planning.week[0].date).toBe("2026-08-17");
    expect(planning.week[6].date).toBe("2026-08-23");
    expect(planning.week[6].isToday).toBe(true);
    expect(isPlanningDashboard(planning)).toBe(true);
  });

  it("rejeita respostas incompletas da API", () => {
    const planning = createDemoPlanning(new Date(2026, 7, 22));

    expect(isPlanningDashboard({ ...planning, weakPoints: undefined })).toBe(false);
  });
});
