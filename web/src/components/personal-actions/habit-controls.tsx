"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";

import {
  createHabitAction,
  setHabitActiveAction,
  setHabitCompletedAction,
} from "@/actions/habits";
import {
  initialCreateMutationState,
  initialInlineMutationState,
  type CreateMutationState,
} from "@/actions/mutation-state";
import type { PersonalHabit } from "@/lib/personal-workspace";

import styles from "../personal-workspace.module.css";
import { MutationSubmitButton } from "./mutation-submit-button";

type HabitControlsProps = {
  habit: PersonalHabit;
  date: string;
  canMutate: boolean;
};

function CancelArchiveButton({ onCancel }: { onCancel: () => void }) {
  const { pending } = useFormStatus();
  return (
    <button disabled={pending} type="button" onClick={onCancel}>
      Cancelar
    </button>
  );
}

export function HabitControls({ habit, date, canMutate }: HabitControlsProps) {
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [feedbackSource, setFeedbackSource] = useState<
    "completed" | "archive" | null
  >(null);
  const [completedState, completedAction] = useActionState(
    setHabitCompletedAction,
    initialInlineMutationState,
  );
  const [archiveState, archiveAction] = useActionState(
    setHabitActiveAction,
    initialInlineMutationState,
  );

  if (!canMutate) return null;
  if (!habit.mutable || !habit.configId) {
    return (
      <p className={styles.readOnlyMessage}>
        Disponível após a atualização dos dados.
      </p>
    );
  }

  const desiredCompleted = !habit.completed;
  const message =
    feedbackSource === "archive"
      ? archiveState.message
      : feedbackSource === "completed"
        ? completedState.message
        : "";
  const showArchiveConfirmation =
    confirmingArchive && archiveState.status !== "success";

  return (
    <div className={styles.habitControls}>
      <form
        action={completedAction}
        onSubmit={() => setFeedbackSource("completed")}
      >
        <input name="configId" type="hidden" value={habit.configId} />
        <input name="date" type="hidden" value={date} />
        <input
          name="completed"
          type="hidden"
          value={String(desiredCompleted)}
        />
        <MutationSubmitButton pendingLabel="Atualizando...">
          {desiredCompleted ? "Marcar como feito" : "Desmarcar"}
        </MutationSubmitButton>
      </form>

      {showArchiveConfirmation ? (
        <div className={styles.deleteConfirmation}>
          <form
            action={archiveAction}
            onSubmit={() => setFeedbackSource("archive")}
          >
            <span>Arquivar este hábito?</span>
            <input name="configId" type="hidden" value={habit.configId} />
            <input name="active" type="hidden" value="false" />
            <MutationSubmitButton pendingLabel="Arquivando...">
              Confirmar arquivo
            </MutationSubmitButton>
            <CancelArchiveButton onCancel={() => setConfirmingArchive(false)} />
          </form>
        </div>
      ) : (
        <button type="button" onClick={() => setConfirmingArchive(true)}>
          Arquivar hábito
        </button>
      )}

      <p aria-live="polite" className={styles.inlineMutationMessage}>
        {message}
      </p>
    </div>
  );
}

type HabitCreateFormProps = { initialItemId: string };

function resolveItemId(
  initialItemId: string,
  state: CreateMutationState,
): string {
  if (state.status === "success" && state.nextItemId) return state.nextItemId;
  return state.submittedItemId ?? initialItemId;
}

export function HabitCreateForm({ initialItemId }: HabitCreateFormProps) {
  const [name, setName] = useState("");
  const [state, action, pending] = useActionState(
    async (previous: CreateMutationState, formData: FormData) => {
      const result = await createHabitAction(previous, formData);
      if (result.status === "success") setName("");
      return result;
    },
    initialCreateMutationState,
  );
  const itemId = resolveItemId(initialItemId, state);

  return (
    <form action={action} className={styles.createForm}>
      <div className={styles.sectionHeading}>
        <h2>Novo hábito</h2>
      </div>
      <input name="itemId" type="hidden" value={itemId} />
      <label>
        <span>Nome do hábito</span>
        <input
          aria-invalid={Boolean(state.fieldErrors.name?.length)}
          disabled={pending}
          maxLength={80}
          name="name"
          onChange={(event) => setName(event.target.value)}
          placeholder="Ex.: Ler vinte páginas"
          required
          value={name}
        />
        {state.fieldErrors.name?.map((error) => (
          <small key={error}>{error}</small>
        ))}
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Salvando..." : "Adicionar hábito"}
      </button>
      <p aria-live="polite" className={styles.formMessage}>
        {state.message}
      </p>
    </form>
  );
}
