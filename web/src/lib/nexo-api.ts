import "server-only";

export async function fetchNexoApi(path: string): Promise<unknown | null> {
  const baseUrl = process.env.NEXO_API_URL?.replace(/\/$/, "");
  if (!baseUrl) {
    return null;
  }

  const apiToken = process.env.NEXO_API_TOKEN;
  if (!apiToken) {
    throw new Error("O token da API do NEXO não foi configurado no servidor web.");
  }

  const response = await fetch(`${baseUrl}${path}`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Nexo-Token": apiToken,
    },
  });

  if (!response.ok) {
    throw new Error(`A API do NEXO respondeu com status ${response.status}.`);
  }

  return response.json();
}
