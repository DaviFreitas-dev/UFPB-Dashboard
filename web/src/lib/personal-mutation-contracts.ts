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

const RoutineMutationItemSchema = z.strictObject({
  id: z.string().trim().min(1).max(80),
  date: z.iso.date(),
  time: z.string().trim().min(1).max(40),
  title: z.string().min(1).max(160),
  completed: z.boolean(),
});

export const CreateRoutineItemResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  created: z.boolean(),
  item: RoutineMutationItemSchema.extend({
    id: z.uuid(),
    time: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d$/),
  }),
});

export const RoutineItemStateResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  changed: z.boolean(),
  item: RoutineMutationItemSchema,
});

export const DeleteRoutineItemResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  id: z.string().trim().min(1).max(80),
  deleted: z.boolean(),
});

export type CreateRoutineItemResponse = z.infer<
  typeof CreateRoutineItemResponseSchema
>;
