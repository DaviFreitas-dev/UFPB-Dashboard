import { AppShell } from "@/components/app-shell";
import { SettingsWorkspace } from "@/components/settings-workspace";
import { loadProfileWorkspace } from "@/lib/profile-workspace-source";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const result = await loadProfileWorkspace();

  return (
    <AppShell currentPath="/configuracoes" user={result.workspace.user}>
      <SettingsWorkspace {...result} />
    </AppShell>
  );
}
