import "server-only";

import { requireAuthorizedSession } from "@/lib/auth-guard";

type ApiProblem = { code: string; message: string; operationId?: string };

export class NexoApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly operationId?: string,
  ) {
    super(message);
    this.name = "NexoApiError";
  }
}

function readApiProblem(payload: unknown): ApiProblem {
  if (!payload || typeof payload !== "object" || !("error" in payload)) {
    return {
      code: "unexpected_api_error",
      message: "Não foi possível concluir a operação.",
    };
  }
  const error = payload.error;
  if (!error || typeof error !== "object") {
    return {
      code: "unexpected_api_error",
      message: "Não foi possível concluir a operação.",
    };
  }
  const errorRecord = error as Record<string, unknown>;
  return {
    code:
      typeof errorRecord.code === "string"
        ? errorRecord.code
        : "unexpected_api_error",
    message:
      typeof errorRecord.message === "string"
        ? errorRecord.message
        : "Não foi possível concluir a operação.",
    operationId:
      typeof errorRecord.operationId === "string"
        ? errorRecord.operationId
        : undefined,
  };
}

export async function requestNexoApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  await requireAuthorizedSession();

  const baseUrl = process.env.NEXO_API_URL?.replace(/\/$/, "");
  const apiToken = process.env.NEXO_API_TOKEN;
  if (!baseUrl || !apiToken) {
    throw new Error("A comunicação segura do NEXO não foi configurada.");
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Nexo-Token": apiToken,
      ...init.headers,
    },
  });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    const problem = readApiProblem(null);
    throw new NexoApiError(response.status, problem.code, problem.message);
  }

  if (!response.ok) {
    const problem = readApiProblem(payload);
    throw new NexoApiError(
      response.status,
      problem.code,
      problem.message,
      problem.operationId,
    );
  }

  return payload as T;
}

export async function fetchNexoApi(path: string): Promise<unknown | null> {
  await requireAuthorizedSession();

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
