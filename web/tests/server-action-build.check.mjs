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

test("o manifesto registra somente funções async do módulo de Server Actions", async () => {
  const path = join(
    nextDir,
    "server",
    "app",
    "tarefas",
    "page",
    "server-reference-manifest.json",
  );
  const manifest = JSON.parse(await readFile(path, "utf8"));
  const exportsFromTaskActions = Object.values(manifest.node)
    .filter((entry) => entry.filename === "src/app/tarefas/actions.ts")
    .map((entry) => entry.exportedName)
    .sort();

  assert.deepEqual(exportsFromTaskActions, ["createTaskAction"]);
});

test("o artefato público transformado não contém configuração privada", async () => {
  const markers = [
    "NEXO_API_TOKEN",
    "NEXO_API_URL",
    process.env.NEXO_API_TOKEN,
  ].filter(Boolean);
  const files = await textFiles(join(nextDir, "static"));

  for (const file of files) {
    const content = await readFile(file, "utf8");
    for (const marker of markers) {
      assert.equal(
        content.includes(marker),
        false,
        `${marker} apareceu no artefato público ${file}`,
      );
    }
  }
});
