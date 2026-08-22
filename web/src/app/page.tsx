import { AppShell } from "@/components/app-shell";
import { TodayDashboard } from "@/components/today-dashboard";
import { loadTodayDashboard } from "@/lib/dashboard-source";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const result = await loadTodayDashboard();

  return (
    <AppShell user={result.dashboard.user}>
      <TodayDashboard {...result} />
    </AppShell>
  );
}
