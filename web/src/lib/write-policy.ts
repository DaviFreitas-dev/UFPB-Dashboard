import "server-only";

export function mutationsUiEnabled(): boolean {
  return (
    process.env.NEXO_WEB_WRITES_ENABLED?.trim().toLowerCase() === "true"
  );
}
