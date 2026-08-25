export type CreateTaskState = {
  status: "idle" | "error" | "success";
  message: string;
  fieldErrors: Partial<Record<"title" | "category" | "date", string[]>>;
  submittedItemId: string | null;
  nextItemId: string | null;
};

export const initialCreateTaskState: CreateTaskState = {
  status: "idle",
  message: "",
  fieldErrors: {},
  submittedItemId: null,
  nextItemId: null,
};
