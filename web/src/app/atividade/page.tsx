import { AppShell } from "@/components/app-shell";
import { ActivityWorkspace } from "@/components/activity-workspace";
import { normalizeRoutineDate } from "@/lib/routine";
import { loadPersonalWorkspace } from "@/lib/personal-workspace-source";

export const dynamic = "force-dynamic";

type ActivityPageProps = { searchParams: Promise<{ date?: string | string[] }> };

export default async function ActivityPage({ searchParams }: ActivityPageProps) {
  const params = await searchParams;
  const rawDate = Array.isArray(params.date) ? params.date[0] : params.date;
  const selectedDate = rawDate ? normalizeRoutineDate(rawDate) : undefined;
  const result = await loadPersonalWorkspace(selectedDate);

  return (
    <AppShell currentPath="/atividade" user={result.workspace.user}>
      <ActivityWorkspace {...result} />
    </AppShell>
  );
}
