import * as z from "zod";


export const CreateTaskResponseSchema = z.strictObject({
  operationId: z.string().min(1).max(80),
  created: z.boolean(),
  task: z.strictObject({
    id: z.uuid(),
    date: z.iso.date(),
    title: z.string().min(1).max(160),
    category: z.string().min(1).max(40),
    completed: z.boolean(),
  }),
});

export type CreateTaskResponse = z.infer<typeof CreateTaskResponseSchema>;
