export type InlineMutationState = {
  status: "idle" | "success" | "error";
  message: string;
};

export type CreateMutationState = InlineMutationState & {
  fieldErrors: Partial<Record<string, string[]>>;
  submittedItemId: string | null;
  nextItemId: string | null;
};

export const initialInlineMutationState: InlineMutationState = {
  status: "idle",
  message: "",
};

export const initialCreateMutationState: CreateMutationState = {
  ...initialInlineMutationState,
  fieldErrors: {},
  submittedItemId: null,
  nextItemId: null,
};
