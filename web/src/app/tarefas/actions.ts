"use server";

import { randomUUID } from "node:crypto";

import { revalidatePath } from "next/cache";
import * as z from "zod";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";

const CreateTaskSchema = z.object({
  itemId: z.uuid({ error: "O identificador do formulário é inválido." }),
  title: z
    .string()
    .trim()
    .min(1, "Informe a tarefa.")
    .max(160, "Use até 160 caracteres."),
  category: z
    .string()
    .trim()
    .min(1, "Informe a categoria.")
    .max(40, "Use até 40 caracteres."),
  date: z.iso.date({ error: "Informe uma data válida." }),
});

export type CreateTaskState = {
  status: "idle" | "error" | "success";
  message: string;
  fieldErrors: Partial<Record<"title" | "category" | "date", string[]>>;
  submittedItemId: string | null;
  nextItemId: string | null;
};

export const initialCreateTaskState: CreateTaskState = {
  status: "idle",
  message: "",
  fieldErrors: {},
  submittedItemId: null,
  nextItemId: null,
};

export async function createTaskAction(
  _previous: CreateTaskState,
  formData: FormData,
): Promise<CreateTaskState> {
  await requireAuthorizedSession();

  const parsed = CreateTaskSchema.safeParse({
    itemId: formData.get("itemId"),
    title: formData.get("title"),
    category: formData.get("category"),
    date: formData.get("date"),
  });

  if (!parsed.success) {
    const errors = z.flattenError(parsed.error).fieldErrors;
    return {
      status: "error",
      message: "Revise os campos indicados.",
      fieldErrors: {
        title: errors.title,
        category: errors.category,
        date: errors.date,
      },
      submittedItemId: String(formData.get("itemId") ?? "") || null,
      nextItemId: null,
    };
  }

  try {
    await requestNexoApi("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        id: parsed.data.itemId,
        date: parsed.data.date,
        title: parsed.data.title,
        category: parsed.data.category,
      }),
    });
  } catch (error) {
    const message =
      error instanceof NexoApiError && error.code === "writes_disabled"
        ? "As alterações ainda não estão disponíveis nesta versão."
        : error instanceof NexoApiError &&
            error.code === "idempotency_conflict"
          ? "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente."
          : "Não foi possível adicionar a tarefa agora.";
    return {
      status: "error",
      message,
      fieldErrors: {},
      submittedItemId: parsed.data.itemId,
      nextItemId: null,
    };
  }

  revalidatePath("/tarefas");
  revalidatePath("/");
  return {
    status: "success",
    message: "Tarefa adicionada.",
    fieldErrors: {},
    submittedItemId: parsed.data.itemId,
    nextItemId: randomUUID(),
  };
}
