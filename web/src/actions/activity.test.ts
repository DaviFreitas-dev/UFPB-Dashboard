import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { requireAuthorizedSession } from "@/lib/auth-guard";
import { requestNexoApi } from "@/lib/nexo-api";
import { RegisterActivityResponseSchema } from "@/lib/personal-mutation-contracts";
import { initialCreateMutationState } from "./mutation-state";
import { registerActivityAction } from "./activity";

const { revalidatePath } = vi.hoisted(() => ({ revalidatePath: vi.fn() }));
vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("@/lib/nexo-api", async (original) => ({
  ...await original<typeof import("@/lib/nexo-api")>(), requestNexoApi: vi.fn(),
}));
const id = "fe55a71b-ab60-4bde-98cc-9bc487a7a4a4";
function form(changes: Record<string, string> = {}) {
  const data = new FormData();
  for (const [key, value] of Object.entries({
    itemId: id, date: "2026-08-25", type: "  Corrida  ", ...changes,
  })) data.set(key, value);
  return data;
}
beforeEach(() => {
  process.env.NEXO_WEB_WRITES_ENABLED = "true";
  vi.mocked(requireAuthorizedSession).mockReset();
  vi.mocked(requireAuthorizedSession).mockResolvedValue({ user: {} } as never);
  vi.mocked(requestNexoApi).mockReset();
  revalidatePath.mockReset();
});
afterEach(() => delete process.env.NEXO_WEB_WRITES_ENABLED);

it("exige sessão antes do gate e bloqueia sem ler formulário", async () => {
  delete process.env.NEXO_WEB_WRITES_ENABLED;
  const get = vi.fn(() => { throw new Error("não ler"); });
  vi.mocked(requireAuthorizedSession).mockRejectedValueOnce(new Error("sem sessão"));
  await expect(registerActivityAction(initialCreateMutationState, { get } as never)).rejects.toThrow("sem sessão");
  const result = await registerActivityAction(initialCreateMutationState, { get } as never);
  expect(get).not.toHaveBeenCalled();
  expect(result.status).toBe("error");
  expect(requestNexoApi).not.toHaveBeenCalled();
});

it.each<Record<string, string>>([{ date: "2026-02-30" }, { type: "Natação" }, { itemId: "fake-id" }])(
  "recusa entrada inválida", async (changes) => {
    const result = await registerActivityAction(initialCreateMutationState, form(changes));
    expect(result.status).toBe("error");
    expect(requestNexoApi).not.toHaveBeenCalled();
  },
);

it("repete o mesmo UUID após erro sem expor detalhes internos", async () => {
  vi.mocked(requestNexoApi).mockRejectedValue(new Error("private credential"));
  const first = await registerActivityAction(initialCreateMutationState, form());
  const retry = await registerActivityAction(first, form());
  expect(retry.submittedItemId).toBe(id);
  expect(retry.nextItemId).toBeNull();
  expect(retry.message).not.toContain("private");
  expect(vi.mocked(requestNexoApi).mock.calls).toEqual([0, 1].map(() => [
    "/v1/activities", { method: "POST", body: JSON.stringify({ id, date: "2026-08-25", type: "Corrida" }) },
    RegisterActivityResponseSchema,
  ]));
  expect(revalidatePath).not.toHaveBeenCalled();
});

it.each(["legacy-id", null])("aceita repetição semântica sem exigir novo ID salvo: %s", async (storedId) => {
  vi.mocked(requestNexoApi).mockResolvedValue({
    operationId: "activity-request-1", created: false, changed: false,
    activity: { id: storedId, date: "2026-08-25", type: "corrida", completed: true },
  });
  const result = await registerActivityAction(initialCreateMutationState, form());
  expect(result.status).toBe("success");
  expect(result.nextItemId).not.toBe(id);
  expect(revalidatePath.mock.calls).toEqual([["/atividade"], ["/"]]);
});

it.each([
  { date: "2026-08-24" }, { type: "Treino" }, { completed: false },
])("não confirma resposta divergente", async (change) => {
  vi.mocked(requestNexoApi).mockResolvedValue({
    operationId: "activity-request-1", created: true, changed: true,
    activity: { id, date: "2026-08-25", type: "Corrida", completed: true, ...change },
  });
  const result = await registerActivityAction(initialCreateMutationState, form());
  expect(result.status).toBe("error");
  expect(revalidatePath).not.toHaveBeenCalled();
});
