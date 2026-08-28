import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "next/headers": fileURLToPath(
        new URL("./node_modules/next/headers.js", import.meta.url),
      ),
      "next/server": fileURLToPath(
        new URL("./node_modules/next/server.js", import.meta.url),
      ),
      "server-only": fileURLToPath(
        new URL("./src/test/server-only.ts", import.meta.url),
      ),
    },
  },
  test: {
    environment: "node",
    globals: true,
    server: {
      deps: {
        inline: [/next-auth/],
      },
    },
    setupFiles: ["./src/test/setup.ts"],
  },
});
