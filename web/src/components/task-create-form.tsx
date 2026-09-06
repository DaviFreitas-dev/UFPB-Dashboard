"use client";

import { useActionState, useState } from "react";

import { createTaskAction } from "@/actions/tasks";
import {
  initialCreateMutationState,
  type CreateMutationState,
} from "@/actions/mutation-state";

import styles from "./personal-workspace.module.css";

type TaskCreateFormProps = {
  initialItemId: string;
  selectedDate: string;
};

export function resolveItemIdAfterAction(
  initialItemId: string,
  state: CreateMutationState,
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
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("Geral");
  const [state, action, pending] = useActionState(
    async (previous: CreateMutationState, data: FormData) => {
      const result = await createTaskAction(previous, data);
      if (result.status === "success") {
        setTitle("");
        setCategory("Geral");
      }
      return result;
    },
    initialCreateMutationState,
  );
  const itemId = resolveItemIdAfterAction(initialItemId, state);

  return (
    <form action={action} className={styles.createForm}>
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
          value={title}
          onChange={(event) => setTitle(event.target.value)}
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
          value={category}
          onChange={(event) => setCategory(event.target.value)}
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
