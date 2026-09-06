"use server";

import { randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import * as z from "zod";
import { ACTIVITY_TYPES } from "@/lib/activity";
import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import { RegisterActivityResponseSchema } from "@/lib/personal-mutation-contracts";
import { mutationsUiEnabled } from "@/lib/write-policy";
import type { CreateMutationState } from "./mutation-state";

const ActivitySchema = z.object({
  itemId: z.uuid(),
  date: z.iso.date({ error: "Informe uma data válida." }),
  type: z.string().trim().refine(
    (value) => ACTIVITY_TYPES.some((type) => type.toLowerCase() === value.toLowerCase()),
    "Escolha uma atividade da lista.",
  ),
});

export async function registerActivityAction(
  _previous: CreateMutationState, formData: FormData,
): Promise<CreateMutationState> {
  await requireAuthorizedSession();
  const unavailable = "As alterações ainda não estão disponíveis nesta versão.";
  if (!mutationsUiEnabled()) {
    return { status: "error", message: unavailable, fieldErrors: {}, submittedItemId: null, nextItemId: null };
  }
  const raw = { itemId: formData.get("itemId"), date: formData.get("date"), type: formData.get("type") };
  const parsed = ActivitySchema.safeParse(raw);
  if (!parsed.success) {
    const id = z.uuid().safeParse(raw.itemId);
    return {
      status: "error", message: id.success ? "Revise os campos indicados." : "O formulário foi renovado. Revise os campos e tente novamente.",
      fieldErrors: z.flattenError(parsed.error).fieldErrors,
      submittedItemId: id.success ? id.data : randomUUID(), nextItemId: null,
    };
  }
  const { itemId: id, date, type } = parsed.data;
  try {
    const response = await requestNexoApi("/v1/activities", {
      method: "POST", body: JSON.stringify({ id, date, type }),
    }, RegisterActivityResponseSchema);
    const confirmed = response.activity;
    if (confirmed.date !== date || confirmed.type.trim().toLowerCase() !== type.toLowerCase() ||
        !confirmed.completed || (response.created && confirmed.id !== id)) {
      throw new Error("Resposta divergente.");
    }
  } catch (error) {
    return {
      status: "error",
      message: error instanceof NexoApiError && error.code === "writes_disabled"
        ? unavailable
        : error instanceof NexoApiError && error.code === "idempotency_conflict"
          ? "Não foi possível confirmar este registro. Atualize a página antes de tentar novamente."
          : "Não foi possível registrar a atividade agora.",
      fieldErrors: {}, submittedItemId: id, nextItemId: null,
    };
  }
  revalidatePath("/atividade");
  revalidatePath("/");
  return {
    status: "success", message: "Atividade registrada.", fieldErrors: {},
    submittedItemId: id, nextItemId: randomUUID(),
  };
}
