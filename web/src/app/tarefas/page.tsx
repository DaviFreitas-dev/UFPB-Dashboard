import { AppShell } from "@/components/app-shell";
import { TasksWorkspace } from "@/components/tasks-workspace";
import { normalizeRoutineDate } from "@/lib/routine";
import { loadPersonalWorkspace } from "@/lib/personal-workspace-source";

export const dynamic = "force-dynamic";

type TasksPageProps = { searchParams: Promise<{ date?: string | string[] }> };

export default async function TasksPage({ searchParams }: TasksPageProps) {
  const params = await searchParams;
  const rawDate = Array.isArray(params.date) ? params.date[0] : params.date;
  const selectedDate = rawDate ? normalizeRoutineDate(rawDate) : undefined;
  const result = await loadPersonalWorkspace(selectedDate);

  return (
    <AppShell currentPath="/tarefas" user={result.workspace.user}>
      <TasksWorkspace {...result} />
    </AppShell>
  );
}
