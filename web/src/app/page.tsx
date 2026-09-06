import { randomUUID } from "node:crypto";
import { AppShell } from "@/components/app-shell";
import { TodayDashboard } from "@/components/today-dashboard";
import { loadTodayDashboard } from "@/lib/dashboard-source";
import { mutationsUiEnabled } from "@/lib/write-policy";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const result = await loadTodayDashboard();

  return (
    <AppShell currentPath="/" user={result.dashboard.user}>
      <TodayDashboard {...result}
        canMutate={result.source === "api" && mutationsUiEnabled()}
        initialTaskId={randomUUID()} initialActivityId={randomUUID()} />
    </AppShell>
  );
}
