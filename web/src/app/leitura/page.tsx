import { randomUUID } from "node:crypto";
import { AppShell } from "@/components/app-shell";
import { ReadingWorkspace } from "@/components/reading-workspace";
import { normalizeRoutineDate } from "@/lib/routine";
import { loadPersonalWorkspace } from "@/lib/personal-workspace-source";
import { mutationsUiEnabled } from "@/lib/write-policy";

export const dynamic = "force-dynamic";

type ReadingPageProps = { searchParams: Promise<{ date?: string | string[] }> };

export default async function ReadingPage({ searchParams }: ReadingPageProps) {
  const params = await searchParams;
  const rawDate = Array.isArray(params.date) ? params.date[0] : params.date;
  const selectedDate = rawDate ? normalizeRoutineDate(rawDate) : undefined;
  const result = await loadPersonalWorkspace(selectedDate);

  return (
    <AppShell currentPath="/leitura" user={result.workspace.user}>
      <ReadingWorkspace {...result}
        canMutate={result.source === "api" && mutationsUiEnabled()}
        initialItemId={randomUUID()} />
    </AppShell>
  );
}
