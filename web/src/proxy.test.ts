import {
  unstable_doesMiddlewareMatch as unstable_doesProxyMatch,
} from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import nextConfig from "../next.config";
import { proxy, config } from "./proxy";

beforeEach(() => {
  process.env.AUTH_SECRET = "auth-secret-exclusivo-de-teste";
});

afterEach(() => {
  delete process.env.AUTH_SECRET;
  delete process.env.NEXO_ALLOWED_GITHUB_ID;
});

describe("proxy de autenticação", () => {
  it.each([
    "/entrar?callbackUrl=%2Ftarefas",
    "/acesso-negado?error=AccessDenied",
    "/api/auth/session?update=1",
    "/api/health?probe=readiness",
    "/_next/static/chunks/app.js?v=1",
    "/_next/image?url=%2Flogo.png&w=64&q=75",
    "/favicon.ico?v=1",
  ])("preserva a superfície pública legítima %s", (url) => {
    expect(unstable_doesProxyMatch({ config, nextConfig, url })).toBe(false);
  });

  it.each([
    "/entrar-secreto",
    "/acesso-negado-extra",
    "/api/authz",
    "/api/health-private",
    "/_next/static-private/chunk.js",
    "/_next/image-private",
    "/favicon.ico-secreto",
  ])("protege a rota parecida, mas não pública %s", (url) => {
    expect(unstable_doesProxyMatch({ config, nextConfig, url })).toBe(true);
  });

  it.each(["/", "/tarefas", "/configuracoes"])(
    "protege a superfície de produto %s",
    (url) => {
      expect(
        unstable_doesProxyMatch({ config, nextConfig, url }),
      ).toBe(true);
    },
  );

  it("redireciona a sessão ausente para a entrada natural", async () => {
    const proxyHandler = proxy as unknown as (
      request: NextRequest,
      event: unknown,
    ) => Promise<Response>;
    const response = await proxyHandler(
      new NextRequest("http://localhost/tarefas"),
      {},
    );

    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.pathname).toBe("/entrar");
    expect(location.searchParams.get("callbackUrl")).toBe(
      "http://localhost/tarefas",
    );
  });
});
