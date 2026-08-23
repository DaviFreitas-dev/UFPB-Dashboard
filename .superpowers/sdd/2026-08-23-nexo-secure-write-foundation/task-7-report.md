# Relatório da Tarefa 7 — autenticação GitHub no portal Next.js

## Resumo

- O portal usa Auth.js v5 com `next-auth@5.0.0-beta.32` fixado sem range e o
  provedor GitHub inferindo `AUTH_GITHUB_ID` e `AUTH_GITHUB_SECRET` apenas no
  servidor.
- A autorização usa exclusivamente o ID numérico imutável do GitHub comparado a
  `NEXO_ALLOWED_GITHUB_ID`. Login, email, nome visível e demais campos não
  concedem acesso.
- Allowlist ausente, vazia ou não numérica falha fechada no login, no proxy e ao
  lado de cada leitura pelo `fetchNexoApi()`.
- Sessões são JWT, com `githubId` e `githubLogin` transportados pelo token. O ID
  é revalidado no `authorized` e em `requireAuthorizedSession()`.
- `/entrar`, `/acesso-negado`, `/api/health` e `/favicon.ico` permanecem
  públicos somente como rotas exatas. `/api/auth/`, `/_next/static/` e
  `/_next/image/` exigem limite real de segmento; nomes parecidos passam pelo
  Proxy do Next.js 16.
- Login, recusa e logout possuem UI natural em português. O logout está
  disponível tanto no sidebar quanto na navegação móvel.
- `NEXO_API_TOKEN`, client secret, allowlist e `AUTH_SECRET` não aparecem no
  HTML nem nos chunks públicos verificados.
- A Tarefa 8 continua dona do helper de mutações e dos formulários de escrita;
  esta tarefa altera somente a fundação de autenticação e o guard de leitura.

## Arquivos

- `web/package.json` e `web/pnpm-lock.yaml` — dependência exata do Auth.js e
  árvore travada.
- `web/src/auth.ts` e `web/src/types/next-auth.d.ts` — GitHub, JWT, páginas e
  callbacks fail-closed.
- `web/src/lib/auth-policy.ts` — comparação pura do ID numérico imutável.
- `web/src/lib/auth-guard.ts` e `web/src/lib/nexo-api.ts` — revalidação da
  sessão imediatamente antes de toda leitura.
- `web/src/proxy.ts` e `web/src/app/api/auth/[...nextauth]/route.ts` — proteção
  do produto e handlers oficiais do Auth.js.
- `web/src/app/entrar/page.tsx`, `web/src/app/acesso-negado/page.tsx` e
  `web/src/components/auth-shell.module.css` — login e recusa públicos,
  acessíveis e responsivos.
- `web/src/components/app-shell.tsx` e
  `web/src/components/app-shell.module.css` — logout no desktop e celular.
- `web/src/test/setup.ts` e `web/vitest.config.ts` — sessão autorizada padrão
  para testes legados e compatibilidade do Vitest com imports ESM do Next 16.
- `web/src/auth.test.ts`, `web/src/proxy.test.ts`,
  `web/src/components/auth-ui.test.tsx`, `web/src/lib/auth-policy.test.ts`,
  `web/src/lib/auth-guard.test.ts` e `web/src/lib/nexo-api.test.ts` — policy,
  callbacks, JWT/sessão, matcher, redirect, guard, leitura e UI.

## RED / GREEN

RED inicial, sem nenhum módulo de produção de autenticação:

```text
pnpm test -- src/lib/auth-policy.test.ts
exit=1
5 suites falharam por módulos ausentes: auth, proxy, auth-guard e auth-policy;
37 testes preexistentes passaram.
```

GREEN da política pura:

```text
pnpm exec vitest run src/lib/auth-policy.test.ts
1 arquivo, 4 testes passaram.
```

RED do guard ao lado da leitura:

```text
pnpm exec vitest run src/lib/nexo-api.test.ts
2 testes falharam: sessão recusada ainda devolvia null e o guard teve 0 chamadas.
```

GREEN do guard ao lado da leitura:

```text
pnpm exec vitest run src/lib/nexo-api.test.ts
1 arquivo, 2 testes passaram.
```

GREEN dos callbacks, JWT e sessão:

```text
pnpm exec vitest run src/auth.test.ts
1 arquivo, 6 testes passaram.
```

GREEN do matcher e redirect real de sessão ausente:

```text
pnpm exec vitest run src/proxy.test.ts
1 arquivo, 8 testes passaram.
```

RED da revisão — lookalikes escapavam do Proxy:

```text
pnpm exec vitest run src/proxy.test.ts
7 testes falharam: /entrar-secreto, /acesso-negado-extra, /api/authz,
/api/health-private, /_next/static-private/chunk.js, /_next/image-private e
/favicon.ico-secreto retornaram false na utility real do Next.
```

GREEN do matcher delimitado:

```text
pnpm exec vitest run src/proxy.test.ts
1 arquivo, 18 testes passaram.
Queries nas rotas públicas legítimas continuaram fora do Proxy; todos os
lookalikes e as rotas de produto ficaram protegidos.
```

RED da auto-revisão responsiva:

```text
pnpm exec vitest run src/components/auth-ui.test.tsx
1 teste falhou: esperado 2 formulários de logout, recebido 1.
```

GREEN da UI com logout desktop e móvel:

```text
pnpm exec vitest run src/components/auth-ui.test.tsx
1 arquivo, 3 testes passaram.
```

GREEN completo final:

```text
pnpm test
18 arquivos, 74 testes passaram.

pnpm lint
exit=0

pnpm typecheck
next typegen e tsc --noEmit concluíram com exit=0.

pnpm build
exit=0; compilação e TypeScript concluídos.
O mapa inclui /api/auth/[...nextauth], /entrar, /acesso-negado e Proxy.

git diff --cached --check
exit=0 antes dos commits.
```

Smoke do build servido localmente, com credenciais exclusivamente fictícias:

```text
GET /api/health               200
GET /entrar                   200; texto e botão presentes
GET /acesso-negado            200; texto e link presentes
GET /api/auth/session         200; body null
GET /tarefas                  307; Location /entrar?callbackUrl=...
HTML/chunks públicos          nenhum nome ou valor de segredo encontrado
```

## Auto-revisão

- Mutar o login para `DaviFreitas-dev` mantendo outro ID faz policy, callback e
  guard recusarem; não existe branch que autorize por username, email ou nome.
- Remover, esvaziar ou preencher a allowlist com texto mantém a autorização em
  `false`. Espaços ao redor de um ID numérico válido são normalizados.
- O `providerAccountId` é a fonte principal do ID; o perfil GitHub fornece
  apenas fallback numérico e o login exibível.
- O Proxy faz apenas a checagem otimista e o redirect. O acesso aos dados
  repete a checagem autoritativa como primeira operação de `fetchNexoApi()`.
- O matcher exige fim de pathname nas páginas, health e favicon, e `(?:/|$)`
  nos prefixos internos. A utility real do Next cobre queries legítimas, sete
  lookalikes e três rotas de produto representativas.
- A sessão pública sem cookie retorna `null`; uma rota protegida sem cookie
  redireciona para `/entrar` conservando o callback URL.
- O build foi varrido em `.next/static` e nos HTMLs prerenderizados de login e
  recusa. Tokens, client secret, allowlist e segredo de sessão não aparecem.
- O Auth.js não foi importado por Client Components. Formulários de login e
  logout são Server Actions; nenhuma variável privada é passada por props.
- Os botões e links têm foco visível. Transições novas usam 180 ms somente sob
  `prefers-reduced-motion: no-preference`.
- A revisão detectou e corrigiu a ausência de logout em telas menores que
  880 px; a navegação móvel agora possui sua própria ação de saída.
- Não houve generalização do cliente de mutações, formulário de tarefa, push,
  PR, merge, deploy, login real ou chamada ao Google Sheets.

## Riscos e pendências

- O fluxo OAuth real não foi executado por restrição da tarefa. A configuração
  do GitHub OAuth App, seu callback e os secrets reais ainda precisam de smoke
  controlado no ambiente de deploy.
- `next-auth` continua beta e foi deliberadamente fixado em
  `5.0.0-beta.32`. Um upgrade deve repetir testes de callback, proxy, HTML e
  bundle antes de alterar a versão.
- O Next 16.3.2 instalado não publica `exports` para `next/server` no Node ESM
  e ainda exporta a utility experimental com o nome legado
  `unstable_doesMiddlewareMatch`. Os aliases e o inline de Vitest são somente
  infraestrutura de teste e devem ser revistos quando Next/Auth.js mudarem.
- A Vercel ativa automaticamente `trustHost` no Auth.js. Um `next start` local
  em modo produção precisa de `AUTH_TRUST_HOST=1` ou `AUTH_URL` explícito; sem
  isso a rota de sessão falha fechada com `UntrustedHost`.

## Hashes

- Base da Tarefa 7: `c5637babe2aef87aa314426d3b246ddf289c1cbc`
- Implementação: `2b8c14fcde089ec1fef59ad88434d8eb93ba3cba`
- Correção responsiva: `aef0b46c5386643d06c9eecbb819be578ee3b0a5`
- Correção do matcher: `0d6bf66bb2cf40caf22f5c3b45df75dfddb609d7`
- SHA-256 `web/package.json`: `32a7ff679b605db970bd538601157b63179f75fdcb2ecdc5ac9c3c71b96417eb`
- SHA-256 `web/pnpm-lock.yaml`: `fab4673c950caa3b06563c2cb2adffdf4387adf853bbd15af160524ba7af4cb7`
- SHA-256 `web/src/auth.ts`: `8d33506189eed2930c9dae03300e4ec14d93985b2aaa85d1834deb6d0ddb62b2`
- SHA-256 `web/src/auth.test.ts`: `e6f43f5837377d638a824f7b4ad310056cb509342781b37e49481bc4064ee66a`
- SHA-256 `web/src/proxy.ts`: `0b22d33e4162ef3c963b1745a8799e685b9dda6b9023a8d0c7b19876d549c168`
- SHA-256 `web/src/proxy.test.ts`: `593e3f459bf0af8a939e136b7749f0fab5758e0107dd9430abf491d0999a7f91`
- SHA-256 `web/src/lib/auth-policy.ts`: `5d3714d64033499a55381fdf53a0b045b6b3322c6bc7ccfa826dfacebc1a30a0`
- SHA-256 `web/src/lib/auth-policy.test.ts`: `5e0e8bbc58abe1d65cec9378a2d9f72a1cf59d4e91896a85cf807a6d3efc90af`
- SHA-256 `web/src/lib/auth-guard.ts`: `bebb3842789e37139918d6bc0ab79d346d6395c4ae5d75ef76a785bdd2d85918`
- SHA-256 `web/src/lib/auth-guard.test.ts`: `3f46a5f514cab352415617e43eb610b8d033d1972f049b7843273a99e331d047`
- SHA-256 `web/src/lib/nexo-api.ts`: `f8e2b7d60a2af73b1e94ce43e215e1473f0fbe8bd19a4ed7fccb52613db907af`
- SHA-256 `web/src/lib/nexo-api.test.ts`: `889dd3f0b8c4dc6a338cdf408807e9b9655a0182e688f5e96fd591ca02f22211`
- SHA-256 `web/src/components/app-shell.tsx`: `9522cae7f89eee855b9256a9388b77c33c985e84bd33770ff5bcc9aaccc8abb3`
- SHA-256 `web/src/components/app-shell.module.css`: `334248c1edf273ae420f4ffc3e156c91f000cd73f4873669e27c3053b7a9cc2f`
- SHA-256 `web/src/components/auth-shell.module.css`: `d3328aac0e8855b482b0d925820866a4081725c3d48cb7fa759728361fec3537`
- SHA-256 `web/src/components/auth-ui.test.tsx`: `5dd02914b8cd4e686e327aa420a94854df9d1793bf1a4d80708d0b6c9c1052d1`
- SHA-256 `web/src/app/entrar/page.tsx`: `b7aaa29cd7ad62aa2e1d7aafe3ca07fcf88fdf3e5b2db94e0d587de0a1a283e9`
- SHA-256 `web/src/app/acesso-negado/page.tsx`: `55e9882186d899660ada37176150cbd293370994b2affa4c6d7025c994c80c25`
- SHA-256 `web/src/app/api/auth/[...nextauth]/route.ts`: `c3e8185d66af3fe7019dd236a463365cce7e1e8dcaea2a7c3b8f0b103e930ce4`
- SHA-256 `web/src/test/setup.ts`: `c371e3b9482de2ad6f2793358b63f2f383535b88d3807cbbfd554c9f4a9be42e`
- SHA-256 `web/src/types/next-auth.d.ts`: `1dc8c4ca42928c400c82f2bde64a526621cecda06b5d7f33ecfec4e450233c2b`
- SHA-256 `web/vitest.config.ts`: `78e89ce6981e2b195b855ae58d2e8e2944b0f2e947ab0f5f630f9d1afc1023bb`
