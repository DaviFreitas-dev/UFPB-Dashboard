"use client";

import { useFormStatus } from "react-dom";

type MutationSubmitButtonProps = {
  children: string;
  pendingLabel: string;
};

export function MutationSubmitButton({
  children,
  pendingLabel,
}: MutationSubmitButtonProps) {
  const { pending } = useFormStatus();

  return (
    <button disabled={pending} type="submit">
      {pending ? pendingLabel : children}
    </button>
  );
}
