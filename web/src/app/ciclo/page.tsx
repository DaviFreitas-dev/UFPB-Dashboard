import { AppShell } from "@/components/app-shell";
import { StudyCycle } from "@/components/study-cycle";
import { loadStudyWorkspace } from "@/lib/study-workspace-source";

export const dynamic = "force-dynamic";

export default async function CyclePage() {
  const result = await loadStudyWorkspace();

  return <AppShell currentPath="/ciclo" user={result.studies.user}><StudyCycle {...result} /></AppShell>;
}
