import { AppShell } from "@/components/app-shell";
import { AchievementsWorkspace } from "@/components/achievements-workspace";
import { loadProfileWorkspace } from "@/lib/profile-workspace-source";

export const dynamic = "force-dynamic";

export default async function AchievementsPage() {
  const result = await loadProfileWorkspace();

  return (
    <AppShell currentPath="/conquistas" user={result.workspace.user}>
      <AchievementsWorkspace {...result} />
    </AppShell>
  );
}
