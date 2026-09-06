"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";

import {
  createRoutineItemAction,
  deleteRoutineItemAction,
  setRoutineItemCompletedAction,
} from "@/actions/routine";
import {
  initialCreateMutationState,
  initialInlineMutationState,
  type CreateMutationState,
} from "@/actions/mutation-state";
import type { RoutineItem } from "@/lib/routine";

import styles from "../routine-dashboard.module.css";
import { MutationSubmitButton } from "./mutation-submit-button";

type RoutineControlsProps = {
  item: RoutineItem;
  canMutate: boolean;
  compact?: boolean;
};

function CancelDeleteButton({ onCancel }: { onCancel: () => void }) {
  const { pending } = useFormStatus();
  return (
    <button disabled={pending} type="button" onClick={onCancel}>
      Cancelar exclusão
    </button>
  );
}

export function RoutineControls({ item, canMutate, compact = false }: RoutineControlsProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [feedbackSource, setFeedbackSource] = useState<
    "state" | "delete" | null
  >(null);
  const [state, stateAction] = useActionState(
    setRoutineItemCompletedAction,
    initialInlineMutationState,
  );
  const [deleteState, deleteAction] = useActionState(
    deleteRoutineItemAction,
    initialInlineMutationState,
  );

  if (!canMutate) return null;
  if (item.kind === "fixed") {
    return (
      <p className={styles.readOnlyMessage}>
        Check-in disponível na próxima etapa.
      </p>
    );
  }
  if (!item.mutable || !item.sourceId) {
    return (
      <p className={styles.readOnlyMessage}>
        Disponível após a atualização dos dados.
      </p>
    );
  }

  const targetCompleted = !item.completed;
  const message =
    feedbackSource === "delete"
      ? deleteState.message
      : feedbackSource === "state"
        ? state.message
        : "";
  const showDeleteConfirmation =
    confirmingDelete && deleteState.status !== "success";

  return (
    <div className={styles.routineControls}>
      <form action={stateAction} onSubmit={() => setFeedbackSource("state")}>
        <input name="id" type="hidden" value={item.sourceId} />
        <input
          name="completed"
          type="hidden"
          value={String(targetCompleted)}
        />
        <MutationSubmitButton pendingLabel="Atualizando...">
          {targetCompleted ? "Concluir compromisso" : "Reabrir compromisso"}
        </MutationSubmitButton>
      </form>

      {!compact && (showDeleteConfirmation ? (
        <div className={styles.deleteConfirmation}>
          <form
            action={deleteAction}
            onSubmit={() => setFeedbackSource("delete")}
          >
            <span>Excluir este compromisso?</span>
            <input name="id" type="hidden" value={item.sourceId} />
            <MutationSubmitButton pendingLabel="Excluindo...">
              Confirmar exclusão
            </MutationSubmitButton>
            <CancelDeleteButton onCancel={() => setConfirmingDelete(false)} />
          </form>
        </div>
      ) : (
        <button type="button" onClick={() => setConfirmingDelete(true)}>
          Excluir compromisso
        </button>
      ))}

      <p aria-live="polite" className={styles.inlineMutationMessage}>
        {message}
      </p>
    </div>
  );
}

type RoutineCreateFormProps = {
  initialItemId: string;
  selectedDate: string;
};

function resolveItemId(
  initialItemId: string,
  state: CreateMutationState,
): string {
  if (state.status === "success" && state.nextItemId) return state.nextItemId;
  return state.submittedItemId ?? initialItemId;
}

export function RoutineCreateForm({
  initialItemId,
  selectedDate,
}: RoutineCreateFormProps) {
  const [activity, setActivity] = useState("");
  const [time, setTime] = useState("");
  const [state, action, pending] = useActionState(
    async (previous: CreateMutationState, formData: FormData) => {
      const result = await createRoutineItemAction(previous, formData);
      if (result.status === "success") {
        setActivity("");
        setTime("");
      }
      return result;
    },
    initialCreateMutationState,
  );
  const itemId = resolveItemId(initialItemId, state);

  return (
    <form action={action} className={styles.createForm}>
      <div className={styles.sectionHeading}>
        <h2>Novo compromisso</h2>
      </div>
      <input name="itemId" type="hidden" value={itemId} />
      <input name="date" type="hidden" value={selectedDate} />
      <label>
        <span>Atividade</span>
        <input
          aria-invalid={Boolean(state.fieldErrors.title?.length)}
          disabled={pending}
          maxLength={160}
          name="title"
          onChange={(event) => setActivity(event.target.value)}
          required
          value={activity}
        />
        {state.fieldErrors.title?.map((error) => (
          <small key={error}>{error}</small>
        ))}
      </label>
      <label>
        <span>Horário</span>
        <input
          aria-invalid={Boolean(state.fieldErrors.time?.length)}
          disabled={pending}
          name="time"
          onChange={(event) => setTime(event.target.value)}
          required
          step={60}
          type="time"
          value={time}
        />
        {state.fieldErrors.time?.map((error) => (
          <small key={error}>{error}</small>
        ))}
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Salvando..." : "Adicionar compromisso"}
      </button>
      <p aria-live="polite" className={styles.formMessage}>
        {state.message}
      </p>
    </form>
  );
}
