import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import test from "node:test";

const nextDir = join(process.cwd(), ".next");

async function textFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await textFiles(path)));
    } else if (/\.(?:css|html|js|json|map|txt)$/.test(entry.name)) {
      files.push(path);
    }
  }
  return files;
}

test("os manifestos registram somente as Server Actions previstas", async () => {
  const expectedActions = {
    "src/actions/tasks.ts": ["createTaskAction", "deleteTaskAction", "setTaskCompletedAction"],
    "src/actions/routine.ts": ["createRoutineItemAction", "deleteRoutineItemAction", "setRoutineItemCompletedAction"],
    "src/actions/habits.ts": ["createHabitAction", "setHabitActiveAction", "setHabitCompletedAction"],
    "src/actions/reading.ts": ["createBookAction", "deleteBookAction", "updateBookAction"],
    "src/actions/activity.ts": ["registerActivityAction"],
  };
  const exportsByFile = new Map();
  const manifests = (await textFiles(join(nextDir, "server")))
    .filter((file) => file.endsWith("server-reference-manifest.json"));
  assert.ok(manifests.length > 0, "Nenhum manifesto de Server Actions foi gerado.");
  for (const path of manifests) {
    const manifest = JSON.parse(await readFile(path, "utf8"));
    for (const entry of [...Object.values(manifest.node ?? {}), ...Object.values(manifest.edge ?? {})]) {
      // Login/logout use inline actions outside the personal mutation modules.
      if (!entry.filename?.startsWith("src/actions/")) continue;
      const names = exportsByFile.get(entry.filename) ?? new Set();
      names.add(entry.exportedName);
      exportsByFile.set(entry.filename, names);
    }
  }
  assert.deepEqual([...exportsByFile.keys()].sort(), Object.keys(expectedActions).sort());
  for (const [filename, names] of Object.entries(expectedActions)) {
    assert.deepEqual([...exportsByFile.get(filename)].sort(), [...names].sort(), filename);
  }
});

test("o artefato público transformado não contém configuração privada", async () => {
  const markers = [
    "NEXO_API_TOKEN",
    "NEXO_API_URL",
    "GSHEETS_SERVICE_ACCOUNT_JSON",
    "-----BEGIN PRIVATE KEY-----",
    "private_key_id",
    process.env.NEXO_API_TOKEN,
  ].filter(Boolean);
  const files = await textFiles(join(nextDir, "static"));

  for (const file of files) {
    const content = await readFile(file, "utf8");
    for (const marker of markers) {
      assert.equal(
        content.includes(marker),
        false,
        `Configuração privada apareceu no artefato público ${file}`,
      );
    }
  }
});
