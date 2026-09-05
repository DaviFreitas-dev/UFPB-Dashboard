"use client";

import { useActionState, useState } from "react";
import { createBookAction, deleteBookAction, updateBookAction } from "@/actions/reading";
import {
  initialCreateMutationState, initialInlineMutationState,
  type CreateMutationState, type InlineMutationState,
} from "@/actions/mutation-state";
import styles from "../personal-workspace.module.css";

type Book = {
  id: string | null;
  title: string;
  currentPage: number;
  totalPages: number;
  status: string;
  mutable: boolean;
};

export function ReadingControls({ book, canMutate, compact = false }: {
  book: Book; canMutate: boolean; compact?: boolean;
}) {
  const [page, setPage] = useState(String(book.currentPage));
  const [confirming, setConfirming] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [state, action, pending] = useActionState(
    async (previous: InlineMutationState, data: FormData) => {
      const deleting = data.get("intent") === "delete";
      const result = await (deleting ? deleteBookAction : updateBookAction)(previous, data);
      if (result.status === "success") {
        if (deleting) setDeleted(true);
        else if (data.get("status") === "Concluído") setPage(String(book.totalPages));
      }
      return result;
    },
    initialInlineMutationState,
  );

  if (!canMutate) return null;
  if (!book.mutable || !book.id) {
    return <p className={styles.formMessage}>Controles indisponíveis para este registro antigo.</p>;
  }
  if (deleted) return <p role="status">{state.message}</p>;

  return (
    <div className={styles.readingControls}>
      <form action={action} className={styles.readingProgressForm}>
        <input type="hidden" name="id" value={book.id} />
        <input type="hidden" name="totalPages" value={book.totalPages} />
        <label>
          Página atual
          <input name="currentPage" type="number" min={0} max={book.totalPages}
            step={1} required disabled={pending} value={page}
            onChange={(event) => setPage(event.target.value)} />
        </label>
        <button disabled={pending} type="submit">Salvar leitura</button>
      </form>
      <div className={styles.taskControls}>
        <form action={action}>
          <input type="hidden" name="id" value={book.id} />
          <input type="hidden" name="totalPages" value={book.totalPages} />
          <input type="hidden" name="status" value={book.status === "Concluído" ? "Lendo" : "Concluído"} />
          <button disabled={pending} type="submit">
            {book.status === "Concluído" ? "Voltar a ler" : "Concluir"}
          </button>
        </form>
        {!compact && (confirming ? (
          <form action={action} className={styles.deleteConfirmation}>
            <span>Excluir {book.title}?</span>
            <input type="hidden" name="id" value={book.id} />
            <input type="hidden" name="intent" value="delete" />
            <button disabled={pending} type="submit">Confirmar exclusão</button>
            <button disabled={pending} type="button" onClick={() => setConfirming(false)}>Cancelar</button>
          </form>
        ) : (
          <button disabled={pending} type="button" onClick={() => setConfirming(true)}>Excluir livro</button>
        ))}
      </div>
      <p aria-live="polite" className={styles.formMessage}>{state.message}</p>
    </div>
  );
}

const emptyBook = { title: "", author: "", totalPages: "", dailyGoal: "" };
const fields = [
  { name: "title", label: "Título", maxLength: 160 },
  { name: "author", label: "Autor", maxLength: 120 },
  { name: "totalPages", label: "Total de páginas" },
  { name: "dailyGoal", label: "Meta diária" },
] as const;

export function ReadingCreateForm({ initialItemId }: { initialItemId: string }) {
  const [values, setValues] = useState(emptyBook);
  const [state, action, pending] = useActionState(
    async (previous: CreateMutationState, data: FormData) => {
      const result = await createBookAction(previous, data);
      if (result.status === "success") setValues(emptyBook);
      return result;
    },
    initialCreateMutationState,
  );
  const itemId = state.nextItemId ?? state.submittedItemId ?? initialItemId;
  return (
    <form action={action} className={styles.createForm}>
      <div className={styles.sectionHeading}><h2>Adicionar livro</h2></div>
      <input type="hidden" name="itemId" value={itemId} />
      {fields.map((field) => {
        const numeric = field.name === "totalPages" || field.name === "dailyGoal";
        return (
          <label key={field.name}>
            <span>{field.label}</span>
            <input name={field.name} value={values[field.name]} disabled={pending}
              required={field.name !== "author"} type={numeric ? "number" : "text"}
              min={numeric ? 1 : undefined} max={numeric ? 1_000_000 : undefined}
              step={numeric ? 1 : undefined}
              maxLength={"maxLength" in field ? field.maxLength : undefined}
              aria-invalid={Boolean(state.fieldErrors[field.name]?.length)}
              onChange={(event) => setValues({ ...values, [field.name]: event.target.value })} />
            {state.fieldErrors[field.name]?.map((error) => <small key={error}>{error}</small>)}
          </label>
        );
      })}
      <button type="submit" disabled={pending}>{pending ? "Salvando..." : "Adicionar livro"}</button>
      <p aria-live="polite" className={styles.formMessage}>{state.message}</p>
    </form>
  );
}
