import * as z from "zod";

const TaskSchema = z.strictObject({
  id: z.string().trim().min(1).max(80),
  date: z.iso.date(),
  title: z.string().min(1).max(160),
  category: z.string().min(1).max(40),
  completed: z.boolean(),
});

export const CreateTaskResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  created: z.boolean(),
  task: TaskSchema.extend({ id: z.uuid() }),
});

export const TaskStateResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  changed: z.boolean(),
  task: TaskSchema,
});

export const DeleteTaskResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  id: z.string().trim().min(1).max(80),
  deleted: z.boolean(),
});

export type CreateTaskResponse = z.infer<typeof CreateTaskResponseSchema>;

export const MAX_ROUTINE_ITEM_ID_LENGTH = 512;

export const PersistentRoutineItemIdSchema = z
  .string()
  .trim()
  .min(1)
  .max(MAX_ROUTINE_ITEM_ID_LENGTH)
  .refine((itemId) => itemId !== "." && itemId !== "..");

const ExistingRoutineMutationItemSchema = z.strictObject({
  id: PersistentRoutineItemIdSchema,
  date: z.iso.date(),
  time: z.string().trim().min(1),
  title: z.string().min(1),
  completed: z.boolean(),
});

export const CreateRoutineItemResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  created: z.boolean(),
  item: ExistingRoutineMutationItemSchema.extend({
    id: z.uuid(),
    time: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d$/),
    title: z.string().min(1).max(160),
  }),
});

export const RoutineItemStateResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  changed: z.boolean(),
  item: ExistingRoutineMutationItemSchema,
});

export const DeleteRoutineItemResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  id: PersistentRoutineItemIdSchema,
  deleted: z.boolean(),
});

export type CreateRoutineItemResponse = z.infer<
  typeof CreateRoutineItemResponseSchema
>;

export const PersistentBookIdSchema = z.string().trim().min(1).max(512)
  .refine((id) => id !== "." && id !== "..");

const MutationBookSchema = z.strictObject({
  id: PersistentBookIdSchema,
  title: z.string().min(1),
  author: z.string(),
  currentPage: z.number().int().min(0),
  totalPages: z.number().int().positive(),
  dailyGoal: z.number().int().min(0),
  status: z.enum(["Lendo", "Concluído"]),
}).refine((book) => book.currentPage <= book.totalPages);

export const CreateBookResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  created: z.boolean(),
  book: MutationBookSchema,
});
export const UpdateBookResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  changed: z.boolean(),
  book: MutationBookSchema,
});
export const DeleteBookResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  id: PersistentBookIdSchema,
  deleted: z.boolean(),
});
