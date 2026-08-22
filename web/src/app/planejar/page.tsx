import { AppShell } from "@/components/app-shell";
import { PlanningDashboard } from "@/components/planning-dashboard";
import { loadPlanningDashboard } from "@/lib/planning-source";

export const dynamic = "force-dynamic";

export default async function PlanningPage() {
  const result = await loadPlanningDashboard();

  return (
    <AppShell currentPath="/planejar" user={result.planning.user}>
      <PlanningDashboard {...result} />
    </AppShell>
  );
}
