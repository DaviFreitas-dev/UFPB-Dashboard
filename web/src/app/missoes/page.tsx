import { AppShell } from "@/components/app-shell";
import { StudyMissions } from "@/components/study-missions";
import { loadStudyWorkspace } from "@/lib/study-workspace-source";

export const dynamic = "force-dynamic";

export default async function MissionsPage() {
  const result = await loadStudyWorkspace();

  return <AppShell currentPath="/missoes" user={result.studies.user}><StudyMissions {...result} /></AppShell>;
}
