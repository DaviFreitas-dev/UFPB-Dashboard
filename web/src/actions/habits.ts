"use server";

import { randomUUID } from "node:crypto";

import { revalidatePath } from "next/cache";
import * as z from "zod";

import { requireAuthorizedSession } from "@/lib/auth-guard";
import { NexoApiError, requestNexoApi } from "@/lib/nexo-api";
import {
  CreateHabitResponseSchema,
  HabitCheckinResponseSchema,
  HabitStateResponseSchema,
  PersistentHabitConfigIdSchema,
} from "@/lib/personal-mutation-contracts";
import { mutationsUiEnabled } from "@/lib/write-policy";

import type { CreateMutationState, InlineMutationState } from "./mutation-state";

const CreateHabitSchema = z.object({
  itemId: z.uuid({ error: "O identificador do formulário é inválido." }),
  name: z
    .string()
    .transform((value) => value.trim().replace(/\s+/g, " "))
    .pipe(
      z
        .string()
        .min(1, "Informe o nome do hábito.")
        .max(80, "Use até 80 caracteres."),
    ),
});
const HabitActiveSchema = z.object({
  configId: PersistentHabitConfigIdSchema,
  active: z.enum(["true", "false"]).transform((value) => value === "true"),
});
const HabitCompletedSchema = z.object({
  configId: PersistentHabitConfigIdSchema,
  date: z.iso.date({ error: "Informe uma data válida." }),
  completed: z
    .enum(["true", "false"])
    .transform((value) => value === "true"),
});

const writesDisabledState: InlineMutationState = {
  status: "error",
  message: "As alterações ainda não estão disponíveis nesta versão.",
};
const invalidState: InlineMutationState = {
  status: "error",
  message: "Revise os dados do hábito.",
};

function revalidateHabitViews() {
  revalidatePath("/habitos");
  revalidatePath("/");
}

function habitNameKey(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase("pt-BR");
}

export async function createHabitAction(
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

  const raw = {
    itemId: formData.get("itemId"),
    name: formData.get("name"),
  };
  const parsedItemId = z.uuid().safeParse(raw.itemId);
  const parsed = CreateHabitSchema.safeParse(raw);
  if (!parsed.success) {
    const errors = z.flattenError(parsed.error).fieldErrors;
    return {
      status: "error",
      message: parsedItemId.success
        ? "Revise os campos indicados."
        : "O formulário foi renovado. Revise os campos e tente novamente.",
      fieldErrors: { name: errors.name },
      submittedItemId: parsedItemId.success ? parsedItemId.data : randomUUID(),
      nextItemId: null,
    };
  }

  try {
    const response = await requestNexoApi(
      "/v1/habits",
      {
        method: "POST",
        body: JSON.stringify({ id: parsed.data.itemId, name: parsed.data.name }),
      },
      CreateHabitResponseSchema,
    );
    const flagsConflict = response.created && response.reactivated;
    const wrongCreatedId =
      response.created && response.habit.configId !== parsed.data.itemId;
    if (
      flagsConflict ||
      wrongCreatedId ||
      habitNameKey(response.habit.title) !== habitNameKey(parsed.data.name) ||
      !response.habit.active
    ) {
      throw new NexoApiError(
        200,
        "ambiguous_api_response",
        "A API respondeu com um hábito diferente do solicitado.",
        response.operationId,
      );
    }

    revalidateHabitViews();
    return {
      status: "success",
      message: response.created
        ? "Hábito criado."
        : response.reactivated
          ? "Hábito reativado."
          : "Esse hábito já está ativo.",
      fieldErrors: {},
      submittedItemId: parsed.data.itemId,
      nextItemId: randomUUID(),
    };
  } catch (error) {
    const message =
      error instanceof NexoApiError && error.code === "writes_disabled"
        ? writesDisabledState.message
        : error instanceof NexoApiError && error.code === "ambiguous_api_response"
          ? "Não foi possível confirmar se o hábito foi salvo. Tente novamente."
          : "Não foi possível adicionar o hábito agora.";
    return {
      status: "error",
      message,
      fieldErrors: {},
      submittedItemId: parsed.data.itemId,
      nextItemId: null,
    };
  }
}

export async function setHabitActiveAction(
  _state: InlineMutationState,
  formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return writesDisabledState;

  const parsed = HabitActiveSchema.safeParse({
    configId: formData.get("configId"),
    active: formData.get("active"),
  });
  if (!parsed.success) return invalidState;

  try {
    const response = await requestNexoApi(
      `/v1/habits/${encodeURIComponent(parsed.data.configId)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ active: parsed.data.active }),
      },
      HabitStateResponseSchema,
    );
    if (
      response.habit.configId !== parsed.data.configId ||
      response.habit.active !== parsed.data.active
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
            ? "O hábito não foi encontrado."
            : "Não foi possível atualizar o hábito agora.",
    };
  }

  revalidateHabitViews();
  return {
    status: "success",
    message: parsed.data.active ? "Hábito reativado." : "Hábito arquivado.",
  };
}

export async function setHabitCompletedAction(
  _state: InlineMutationState,
  formData: FormData,
): Promise<InlineMutationState> {
  await requireAuthorizedSession();
  if (!mutationsUiEnabled()) return writesDisabledState;

  const parsed = HabitCompletedSchema.safeParse({
    configId: formData.get("configId"),
    date: formData.get("date"),
    completed: formData.get("completed"),
  });
  if (!parsed.success) return invalidState;

  try {
    const response = await requestNexoApi(
      `/v1/habit-checkins/${encodeURIComponent(parsed.data.configId)}/${parsed.data.date}`,
      {
        method: "PUT",
        body: JSON.stringify({ completed: parsed.data.completed }),
      },
      HabitCheckinResponseSchema,
    );
    if (
      response.checkin.configId !== parsed.data.configId ||
      response.checkin.date !== parsed.data.date ||
      response.checkin.completed !== parsed.data.completed ||
      (parsed.data.completed && response.checkin.logId === null)
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
            ? "O hábito não foi encontrado."
            : "Não foi possível atualizar o hábito agora.",
    };
  }

  revalidateHabitViews();
  return {
    status: "success",
    message: parsed.data.completed
      ? "Hábito marcado como feito."
      : "Hábito desmarcado.",
  };
}
