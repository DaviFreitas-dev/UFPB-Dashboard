import { randomUUID } from "node:crypto";

import { AppShell } from "@/components/app-shell";
import { HabitsWorkspace } from "@/components/habits-workspace";
import { normalizeRoutineDate } from "@/lib/routine";
import { loadPersonalWorkspace } from "@/lib/personal-workspace-source";
import { mutationsUiEnabled } from "@/lib/write-policy";

export const dynamic = "force-dynamic";

type HabitsPageProps = { searchParams: Promise<{ date?: string | string[] }> };

export default async function HabitsPage({ searchParams }: HabitsPageProps) {
  const params = await searchParams;
  const rawDate = Array.isArray(params.date) ? params.date[0] : params.date;
  const selectedDate = rawDate ? normalizeRoutineDate(rawDate) : undefined;
  const result = await loadPersonalWorkspace(selectedDate);

  return (
    <AppShell currentPath="/habitos" user={result.workspace.user}>
      <HabitsWorkspace
        {...result}
        canMutate={result.source === "api" && mutationsUiEnabled()}
        initialItemId={randomUUID()}
      />
    </AppShell>
  );
}
