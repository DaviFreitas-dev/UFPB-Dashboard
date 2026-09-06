"use client";

import { useActionState, useLayoutEffect, useRef, useState } from "react";
import { registerActivityAction } from "@/actions/activity";
import { initialCreateMutationState } from "@/actions/mutation-state";
import { ACTIVITY_TYPES } from "@/lib/activity";
import styles from "../personal-workspace.module.css";

export function ActivityCreateForm({ initialItemId, selectedDate }: {
  initialItemId: string;
  selectedDate: string;
}) {
  const [type, setType] = useState<string>("Treino");
  const [date, setDate] = useState(selectedDate);
  const [state, action, pending] = useActionState(registerActivityAction, initialCreateMutationState);
  const typeRef = useRef<HTMLSelectElement>(null);
  useLayoutEffect(() => {
    // React resets native selects after an action, including unsuccessful writes.
    if (!pending && typeRef.current) typeRef.current.value = type;
  }, [pending, type]);
  const itemId = state.nextItemId ?? state.submittedItemId ?? initialItemId;
  return (
    <form action={action} className={styles.createForm}>
      <div className={styles.sectionHeading}><h2>Registrar atividade</h2></div>
      <input type="hidden" name="itemId" value={itemId} />
      <label>
        <span>Atividade realizada</span>
        <select ref={typeRef} name="type" required value={type} disabled={pending}
          aria-invalid={Boolean(state.fieldErrors.type?.length)}
          onChange={(event) => setType(event.target.value)}>
          {ACTIVITY_TYPES.map((item) => <option key={item}>{item}</option>)}
        </select>
        {state.fieldErrors.type?.map((error) => <small key={error}>{error}</small>)}
      </label>
      <label>
        <span>Data</span>
        <input name="date" type="date" required value={date} disabled={pending}
          aria-invalid={Boolean(state.fieldErrors.date?.length)}
          onChange={(event) => setDate(event.target.value)} />
        {state.fieldErrors.date?.map((error) => <small key={error}>{error}</small>)}
      </label>
      <button type="submit" disabled={pending}>{pending ? "Registrando..." : "Registrar atividade"}</button>
      <p aria-live="polite" className={styles.formMessage}>{state.message}</p>
    </form>
  );
}
