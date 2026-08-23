"use client";

import { useActionState, useEffect, useRef } from "react";

import {
  createTaskAction,
  initialCreateTaskState,
  type CreateTaskState,
} from "@/app/tarefas/actions";

import styles from "./personal-workspace.module.css";

type TaskCreateFormProps = {
  initialItemId: string;
  selectedDate: string;
};

export function resolveItemIdAfterAction(
  initialItemId: string,
  state: CreateTaskState,
): string {
  if (state.status === "success" && state.nextItemId) {
    return state.nextItemId;
  }
  return state.submittedItemId ?? initialItemId;
}

export function TaskCreateForm({
  initialItemId,
  selectedDate,
}: TaskCreateFormProps) {
  const [state, action, pending] = useActionState(
    createTaskAction,
    initialCreateTaskState,
  );
  const formRef = useRef<HTMLFormElement>(null);
  const itemId = resolveItemIdAfterAction(initialItemId, state);

  useEffect(() => {
    if (state.status === "success") {
      formRef.current?.reset();
    }
  }, [state.status, state.submittedItemId]);

  return (
    <form action={action} className={styles.createForm} ref={formRef}>
      <div className={styles.sectionHeading}>
        <h2>Nova tarefa</h2>
      </div>
      <input name="itemId" type="hidden" value={itemId} />
      <input name="date" type="hidden" value={selectedDate} />
      <label>
        <span>O que precisa ser feito?</span>
        <input
          aria-invalid={Boolean(state.fieldErrors.title?.length)}
          disabled={pending}
          maxLength={160}
          name="title"
          required
        />
        {state.fieldErrors.title?.map((error) => (
          <small key={error}>{error}</small>
        ))}
      </label>
      <label>
        <span>Categoria</span>
        <input
          aria-invalid={Boolean(state.fieldErrors.category?.length)}
          defaultValue="Geral"
          disabled={pending}
          maxLength={40}
          name="category"
          required
        />
        {state.fieldErrors.category?.map((error) => (
          <small key={error}>{error}</small>
        ))}
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Salvando..." : "Adicionar tarefa"}
      </button>
      <p aria-live="polite" className={styles.formMessage}>
        {state.message}
      </p>
    </form>
  );
}
