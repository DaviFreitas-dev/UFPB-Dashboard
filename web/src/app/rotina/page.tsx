import { AppShell } from "@/components/app-shell";
import { RoutineDashboard } from "@/components/routine-dashboard";
import { normalizeRoutineDate } from "@/lib/routine";
import { loadRoutineDashboard } from "@/lib/routine-source";

export const dynamic = "force-dynamic";

type RoutinePageProps = {
  searchParams: Promise<{ date?: string | string[] }>;
};

export default async function RoutinePage({ searchParams }: RoutinePageProps) {
  const params = await searchParams;
  const rawDate = Array.isArray(params.date) ? params.date[0] : params.date;
  const selectedDate = normalizeRoutineDate(rawDate);
  const result = await loadRoutineDashboard(selectedDate);

  return (
    <AppShell currentPath="/rotina" user={result.routine.user}>
      <RoutineDashboard {...result} />
    </AppShell>
  );
}
