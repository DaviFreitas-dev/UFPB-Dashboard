import { AppShell } from "@/components/app-shell";
import { MoreDashboard } from "@/components/more-dashboard";
import { loadTodayDashboard } from "@/lib/dashboard-source";

export const dynamic = "force-dynamic";

export default async function MorePage() {
  const result = await loadTodayDashboard();

  return (
    <AppShell currentPath="/mais" user={result.dashboard.user}>
      <MoreDashboard />
    </AppShell>
  );
}
