"use server";

import { randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import * as z from "zod";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateBookResponseSchema, DeleteBookResponseSchema,
  PersistentBookIdSchema, UpdateBookResponseSchema,
} from "@/lib/personal-mutation-contracts";
import { mutationsUiEnabled } from "@/lib/write-policy";
import type { CreateMutationState, InlineMutationState } from "./mutation-state";

const positiveInteger = (message: string) =>
  z.string().trim().regex(/^\d+$/, message)
    .transform(Number).pipe(z.number().int(message).min(1, message).max(1_000_000, message));
const CreateBookSchema = z.object({
  itemId: z.uuid(),
  title: z.string().trim().min(1, "Informe o título.").max(160, "Use até 160 caracteres."),
  author: z.string().trim().max(120, "Use até 120 caracteres."),
  totalPages: positiveInteger("Informe um total positivo."),
  dailyGoal: positiveInteger("Informe uma meta inteira positiva."),
});
const UpdateBookSchema = z.object({
  id: PersistentBookIdSchema,
  totalPages: positiveInteger("Total inválido."),
  currentPage: z.string().trim().regex(/^\d+$/).transform(Number)
    .pipe(z.number().int().min(0).max(1_000_000)).optional(),
  status: z.enum(["Lendo", "Concluído"]).optional(),
}).refine((data) => data.currentPage !== undefined || data.status !== undefined)
  .refine((data) => data.currentPage === undefined || data.currentPage <= data.totalPages);

const disabled: InlineMutationState = {
  status: "error", message: "As alterações ainda não estão disponíveis nesta versão.",
};
const invalid: InlineMutationState = { status: "error", message: "Revise os dados da leitura." };

function revalidateReading() {
  revalidatePath("/leitura");
  revalidatePath("/");
}

function failure(error: unknown, fallback: string): InlineMutationState {
  return {
    status: "error",
    message: error instanceof NexoApiError && error.code === "writes_disabled"
      ? disabled.message
      : error instanceof NexoApiError && error.code === "record_not_found"
        ? "O livro não foi encontrado."
        : error instanceof NexoApiError && error.code === "idempotency_conflict"
          ? "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente."
          : fallback,
  };
}

export async function createBookAction(
  _previous: CreateMutationState, formData: FormData,
): Promise<CreateMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) {
    return { ...disabled, fieldErrors: {}, submittedItemId: null, nextItemId: null };
  }
  const raw = {
    itemId: formData.get("itemId"), title: formData.get("title"),
    author: formData.get("author"), totalPages: formData.get("totalPages"),
    dailyGoal: formData.get("dailyGoal"),
  };
  const parsed = CreateBookSchema.safeParse(raw);
  if (!parsed.success) {
    const id = z.uuid().safeParse(raw.itemId);
    return {
      status: "error",
      message: id.success ? "Revise os campos indicados." : "O formulário foi renovado. Revise os campos e tente novamente.",
      fieldErrors: z.flattenError(parsed.error).fieldErrors,
      submittedItemId: id.success ? id.data : randomUUID(), nextItemId: null,
    };
  }
  const { itemId: id, ...fields } = parsed.data;
  const requested = { id, ...fields };
  try {
    const response = await requestNexoApi("/v1/books", {
      method: "POST", body: JSON.stringify(requested),
    }, CreateBookResponseSchema);
    if (response.book.id !== id || response.book.title !== fields.title ||
        response.book.author !== fields.author || response.book.totalPages !== fields.totalPages ||
        response.book.dailyGoal !== fields.dailyGoal) {
      throw new Error("Resposta divergente.");
    }
  } catch (error) {
    return {
      ...failure(error, "Não foi possível salvar o livro agora."),
      fieldErrors: {}, submittedItemId: id, nextItemId: null,
    };
  }
  revalidateReading();
  return {
    status: "success", message: "Livro adicionado.", fieldErrors: {},
    submittedItemId: id, nextItemId: randomUUID(),
  };
}

export async function updateBookAction(
  _previous: InlineMutationState, formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return disabled;
  const parsed = UpdateBookSchema.safeParse({
    id: formData.get("id"), totalPages: formData.get("totalPages"),
    currentPage: formData.get("currentPage") ?? undefined,
    status: formData.get("status") ?? undefined,
  });
  if (!parsed.success) return invalid;
  const { id, totalPages, ...patch } = parsed.data;
  let confirmedStatus: string;
  try {
    const response = await requestNexoApi(`/v1/books/${encodeURIComponent(id)}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }, UpdateBookResponseSchema);
    const book = response.book;
    const completes = patch.status === "Concluído" ||
      (patch.status === undefined && patch.currentPage === totalPages);
    if (book.id !== id || book.totalPages !== totalPages ||
        (patch.status !== undefined && book.status !== patch.status) ||
        (completes && (book.currentPage !== totalPages || book.status !== "Concluído")) ||
        (!completes && patch.currentPage !== undefined && book.currentPage !== patch.currentPage)) {
      throw new Error("Resposta divergente.");
    }
    confirmedStatus = book.status;
  } catch (error) {
    return failure(error, "Não foi possível atualizar a leitura agora.");
  }
  revalidateReading();
  return {
    status: "success",
    message: patch.status === "Lendo" ? "Leitura reaberta."
      : confirmedStatus === "Concluído" ? "Leitura concluída." : "Leitura atualizada.",
  };
}

export async function deleteBookAction(
  _previous: InlineMutationState, formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return disabled;
  const parsed = PersistentBookIdSchema.safeParse(formData.get("id"));
  if (!parsed.success) return invalid;
  try {
    const response = await requestNexoApi(`/v1/books/${encodeURIComponent(parsed.data)}`, {
      method: "DELETE",
    }, DeleteBookResponseSchema);
    if (response.id !== parsed.data) throw new Error("Resposta divergente.");
  } catch (error) {
    return failure(error, "Não foi possível excluir o livro agora.");
  }
  revalidateReading();
  return { status: "success", message: "Livro excluído." };
}
