"use client";

import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";

import {
  deleteTaskAction,
  setTaskCompletedAction,
} from "@/actions/tasks";
import { initialInlineMutationState } from "@/actions/mutation-state";
import type { PersonalTask } from "@/lib/personal-workspace";

import styles from "../personal-workspace.module.css";
import { MutationSubmitButton } from "./mutation-submit-button";

type TaskControlsProps = {
  task: PersonalTask;
  canMutate: boolean;
};

function CancelDeleteButton({ onCancel }: { onCancel: () => void }) {
  const { pending } = useFormStatus();

  return (
    <button disabled={pending} type="button" onClick={onCancel}>
      Cancelar exclusão
    </button>
  );
}

export function TaskControls({ task, canMutate }: TaskControlsProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [feedbackSource, setFeedbackSource] = useState<
    "state" | "delete" | null
  >(null);
  const [state, stateAction] = useActionState(
    setTaskCompletedAction,
    initialInlineMutationState,
  );
  const [deleteState, deleteAction] = useActionState(
    deleteTaskAction,
    initialInlineMutationState,
  );

  if (!canMutate || !task.mutable) return null;

  const targetCompleted = !task.completed;
  const message =
    feedbackSource === "delete"
      ? deleteState.message
      : feedbackSource === "state"
        ? state.message
        : "";
  const showDeleteConfirmation =
    confirmingDelete && deleteState.status !== "success";

  return (
    <div className={styles.taskControls}>
      <form action={stateAction} onSubmit={() => setFeedbackSource("state")}>
        <input name="id" type="hidden" value={task.id} />
        <input
          name="completed"
          type="hidden"
          value={String(targetCompleted)}
        />
        <MutationSubmitButton pendingLabel="Atualizando...">
          {targetCompleted ? "Concluir tarefa" : "Reabrir tarefa"}
        </MutationSubmitButton>
      </form>

      {showDeleteConfirmation ? (
        <div className={styles.deleteConfirmation}>
          <form
            action={deleteAction}
            onSubmit={() => setFeedbackSource("delete")}
          >
            <span>Excluir esta tarefa?</span>
            <input name="id" type="hidden" value={task.id} />
            <MutationSubmitButton pendingLabel="Excluindo...">
              Confirmar exclusão
            </MutationSubmitButton>
            <CancelDeleteButton onCancel={() => setConfirmingDelete(false)} />
          </form>
        </div>
      ) : (
        <button type="button" onClick={() => setConfirmingDelete(true)}>
          Excluir tarefa
        </button>
      )}

      <p aria-live="polite" className={styles.inlineMutationMessage}>
        {message}
      </p>
    </div>
  );
}
