import { describe, expect, it } from "vitest";

import { createDemoDashboard } from "./demo-dashboard";
import {
  deadlineLabel,
  formatDatePtBr,
  isTodayDashboard,
  ratio,
} from "./dashboard";

describe("ratio", () => {
  it("limita o progresso entre zero e um", () => {
    expect(ratio(-4, 10)).toBe(0);
    expect(ratio(5, 10)).toBe(0.5);
    expect(ratio(15, 10)).toBe(1);
    expect(ratio(5, 0)).toBe(0);
  });
});

describe("formatDatePtBr", () => {
  it("formata uma data ISO sem deslocar o dia", () => {
    expect(formatDatePtBr("2026-08-22")).toBe("22 de agosto de 2026");
  });
});

describe("deadlineLabel", () => {
  it("descreve prazos futuros e vencidos", () => {
    expect(deadlineLabel("2026-08-22", "2026-08-22")).toBe("hoje");
    expect(deadlineLabel("2026-08-23", "2026-08-22")).toBe("amanhã");
    expect(deadlineLabel("2026-08-27", "2026-08-22")).toBe("em 5 dias");
    expect(deadlineLabel("2026-08-20", "2026-08-22")).toBe("2 dias em atraso");
  });
});

describe("isTodayDashboard", () => {
  it("aceita o contrato completo do painel", () => {
    expect(isTodayDashboard(createDemoDashboard(new Date(2026, 7, 22)))).toBe(true);
  });

  it("recusa dados incompletos vindos da API", () => {
    const dashboard = createDemoDashboard(new Date(2026, 7, 22));

    expect(
      isTodayDashboard({
        ...dashboard,
        user: { ...dashboard.user, xp: "3420" },
      }),
    ).toBe(false);
    expect(isTodayDashboard({ ...dashboard, agenda: [{ id: "sem-campos" }] })).toBe(
      false,
    );
  });
});
