"use server";

import { randomUUID } from "node:crypto";

import { revalidatePath } from "next/cache";
import * as z from "zod";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateRoutineItemResponseSchema,
  DeleteRoutineItemResponseSchema,
  RoutineItemStateResponseSchema,
} from "@/lib/personal-mutation-contracts";
import { mutationsUiEnabled } from "@/lib/write-policy";

import type { CreateMutationState, InlineMutationState } from "./mutation-state";

const TimeSchema = z
  .string()
  .trim()
  .regex(
    /^(?:[01]\d|2[0-3]):[0-5]\d$/,
    "Informe um horário válido no formato HH:MM.",
  );
const CreateRoutineItemSchema = z.object({
  itemId: z.uuid({ error: "O identificador do formulário é inválido." }),
  title: z
    .string()
    .trim()
    .min(1, "Informe a atividade.")
    .max(160, "Use até 160 caracteres."),
  time: TimeSchema,
  date: z.iso.date({ error: "Informe uma data válida." }),
});
const RoutineItemIdSchema = z.string().trim().min(1);
const RoutineItemStateSchema = z.object({
  id: RoutineItemIdSchema,
  completed: z.enum(["true", "false"]).transform((value) => value === "true"),
});
const DeleteRoutineItemSchema = z.object({ id: RoutineItemIdSchema });

const writesDisabledState: InlineMutationState = {
  status: "error",
  message: "As alterações ainda não estão disponíveis nesta versão.",
};
const invalidInlineState: InlineMutationState = {
  status: "error",
  message: "Revise os dados do compromisso.",
};

function revalidateRoutineViews() {
  revalidatePath("/rotina");
  revalidatePath("/");
}

export async function createRoutineItemAction(
  _previous: CreateMutationState,
  formData: FormData,
): Promise<CreateMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) {
    return {
      ...writesDisabledState,
      fieldErrors: {},
      submittedItemId: null,
      nextItemId: null,
    };
  }

  const rawFormData = {
    itemId: formData.get("itemId"),
    title: formData.get("title"),
    time: formData.get("time"),
    date: formData.get("date"),
  };
  const parsedItemId = z.uuid().safeParse(rawFormData.itemId);
  const parsed = CreateRoutineItemSchema.safeParse(rawFormData);
  if (!parsed.success) {
    const errors = z.flattenError(parsed.error).fieldErrors;
    return {
      status: "error",
      message: parsedItemId.success
        ? "Revise os campos indicados."
        : "O formulário foi renovado. Revise os campos e tente novamente.",
      fieldErrors: {
        title: errors.title,
        time: errors.time,
        date: errors.date,
      },
      submittedItemId: parsedItemId.success
        ? parsedItemId.data
        : randomUUID(),
      nextItemId: null,
    };
  }

  const requestedItem = {
    id: parsed.data.itemId,
    date: parsed.data.date,
    time: parsed.data.time,
    title: parsed.data.title,
  };

  try {
    const response = await requestNexoApi(
      "/v1/routine-items",
      {
        method: "POST",
        body: JSON.stringify(requestedItem),
      },
      CreateRoutineItemResponseSchema,
    );
    if (
      response.item.id !== requestedItem.id ||
      response.item.date !== requestedItem.date ||
      response.item.time !== requestedItem.time ||
      response.item.title !== requestedItem.title
    ) {
      throw new NexoApiError(
        200,
        "ambiguous_api_response",
        "A API respondeu com um compromisso diferente do solicitado.",
        response.operationId,
      );
    }
  } catch (error) {
    const message =
      error instanceof NexoApiError && error.code === "writes_disabled"
        ? writesDisabledState.message
        : error instanceof NexoApiError && error.code === "idempotency_conflict"
          ? "Este formulário já foi enviado com outros dados. Atualize a página e tente novamente."
          : error instanceof NexoApiError &&
              error.code === "ambiguous_api_response"
            ? "Não foi possível confirmar se o compromisso foi salvo. Tente novamente."
            : "Não foi possível adicionar o compromisso agora.";
    return {
      status: "error",
      message,
      fieldErrors: {},
      submittedItemId: parsed.data.itemId,
      nextItemId: null,
    };
  }

  revalidateRoutineViews();
  return {
    status: "success",
    message: "Compromisso adicionado.",
    fieldErrors: {},
    submittedItemId: parsed.data.itemId,
    nextItemId: randomUUID(),
  };
}

export async function setRoutineItemCompletedAction(
  _state: InlineMutationState,
  formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return writesDisabledState;

  const parsed = RoutineItemStateSchema.safeParse({
    id: formData.get("id"),
    completed: formData.get("completed"),
  });
  if (!parsed.success) return invalidInlineState;

  try {
    const response = await requestNexoApi(
      `/v1/routine-items/${encodeURIComponent(parsed.data.id)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ completed: parsed.data.completed }),
      },
      RoutineItemStateResponseSchema,
    );
    if (
      response.item.id !== parsed.data.id ||
      response.item.completed !== parsed.data.completed
    ) {
      throw new NexoApiError(
        200,
        "ambiguous_api_response",
        "A API respondeu com um estado diferente do solicitado.",
        response.operationId,
      );
    }
  } catch (error) {
    return {
      status: "error",
      message:
        error instanceof NexoApiError && error.code === "writes_disabled"
          ? writesDisabledState.message
          : error instanceof NexoApiError && error.code === "record_not_found"
            ? "O compromisso não foi encontrado."
            : "Não foi possível atualizar o compromisso agora.",
    };
  }

  revalidateRoutineViews();
  return {
    status: "success",
    message: parsed.data.completed
      ? "Compromisso concluído."
      : "Compromisso reaberto.",
  };
}

export async function deleteRoutineItemAction(
  _state: InlineMutationState,
  formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return writesDisabledState;

  const parsed = DeleteRoutineItemSchema.safeParse({ id: formData.get("id") });
  if (!parsed.success) return invalidInlineState;

  try {
    const response = await requestNexoApi(
      `/v1/routine-items/${encodeURIComponent(parsed.data.id)}`,
      { method: "DELETE" },
      DeleteRoutineItemResponseSchema,
    );
    if (response.id !== parsed.data.id) {
      throw new NexoApiError(
        200,
        "ambiguous_api_response",
        "A API respondeu com um compromisso diferente do solicitado.",
        response.operationId,
      );
    }
  } catch (error) {
    return {
      status: "error",
      message:
        error instanceof NexoApiError && error.code === "writes_disabled"
          ? writesDisabledState.message
          : "Não foi possível excluir o compromisso agora.",
    };
  }

  revalidateRoutineViews();
  return { status: "success", message: "Compromisso excluído." };
}
