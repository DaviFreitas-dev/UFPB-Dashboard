import { describe, expect, it } from "vitest";

import { createDemoRoutine } from "./demo-routine";
import {
  addRoutineDays,
  isRoutineDashboard,
  normalizeRoutineDate,
} from "./routine";

describe("routine contract", () => {
  it("normaliza datas válidas e recusa calendários impossíveis", () => {
    const fallback = new Date(2026, 7, 22);

    expect(normalizeRoutineDate("2026-08-24", fallback)).toBe("2026-08-24");
    expect(normalizeRoutineDate("2026-02-31", fallback)).toBe("2026-08-22");
    expect(addRoutineDays("2026-08-31", 1)).toBe("2026-09-01");
  });

  it("valida o contrato completo e rejeita respostas incompletas", () => {
    const routine = createDemoRoutine(new Date(2026, 7, 22));

    expect(isRoutineDashboard(routine)).toBe(true);
    expect(isRoutineDashboard({ ...routine, items: undefined })).toBe(false);
  });
});
