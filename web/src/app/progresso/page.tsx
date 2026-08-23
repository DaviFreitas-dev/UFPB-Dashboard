import { AppShell } from "@/components/app-shell";
import { StudyProgress } from "@/components/study-progress";
import { loadStudyWorkspace } from "@/lib/study-workspace-source";

export const dynamic = "force-dynamic";

export default async function ProgressPage() {
  const result = await loadStudyWorkspace();

  return <AppShell currentPath="/progresso" user={result.studies.user}><StudyProgress {...result} /></AppShell>;
}
