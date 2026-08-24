# Relatório da Tarefa 8 — formulário protegido e Server Action de tarefas

## Resumo

- O cliente `server-only` do NEXO foi generalizado para mutações com sessão
  autorizada, token privado entre servidores, JSON, `no-store` e parsing
  defensivo do envelope de erro, sem alterar o fallback `null` das leituras.
- A Server Action de criação revalida a sessão antes de ler o `FormData`, valida
  e normaliza com Zod 4.4.3, chama exatamente `POST /v1/tasks` e revalida
  `/tarefas` e `/` somente depois da confirmação da API.
- O formulário usa um UUID estável durante validações, falhas da API e retries.
  Um UUID novo passa a ser usado somente depois de sucesso confirmado.
- A interface mostra o formulário somente quando a fonte é a API real e
  `NEXO_WEB_WRITES_ENABLED=true`. Flag ausente ou inválida mantém todos os
  controles de escrita ocultos; o gate independente do FastAPI não foi alterado.
- Inputs não controlados preservam título e categoria em falhas. O botão e os
  campos ficam indisponíveis durante a submissão, as mensagens são naturais em
  português e o formulário mantém HTML progressivo e acessível.
- Nenhuma escrita real, OAuth real, chamada ao Google Sheets, push, PR, merge ou
  deploy foi executado.

## Arquivos

- `web/package.json` e `web/pnpm-lock.yaml` — Zod fixado em `4.4.3` após a árvore
  existente do Auth.js.
- `web/src/lib/write-policy.ts` e `.test.ts` — gate de UI fechado por padrão.
- `web/src/lib/nexo-api.ts` e `.test.ts` — cliente genérico de request, erro
  estruturado, autenticação e header privado servidor a servidor.
- `web/src/app/tarefas/actions.ts` e `.test.ts` — validação Zod, POST exato,
  mensagens seguras, retry idempotente e revalidação pós-sucesso.
- `web/src/components/task-create-form.tsx` — formulário com pending state,
  preservação de valores e rotação segura do UUID.
- `web/src/components/task-ui.test.tsx` — gate off/on, fonte demo/API, HTML,
  acessibilidade, segredo ausente e ciclo do UUID.
- `web/src/components/tasks-workspace.tsx` e
  `web/src/app/tarefas/page.tsx` — composição server-side do gate e UUID inicial.
- `web/src/components/personal-workspace.module.css` — layout responsivo, foco
  visível e transições de 180 ms somente quando movimento é permitido.

## Evidência RED / GREEN

RED do gate de UI, antes do módulo de produção:

```text
pnpm test -- src/lib/write-policy.test.ts
exit=1
Cannot find module './write-policy'
```

RED do cliente de mutações, antes da generalização:

```text
pnpm test -- src/lib/nexo-api.test.ts
exit=1
4 testes falharam: requestNexoApi is not a function
```

RED da Server Action, antes do módulo de produção:

```text
pnpm test -- src/app/tarefas/actions.test.ts
exit=1
Cannot find module '/src/app/tarefas/actions'
```

RED da UI, antes do formulário:

```text
pnpm test -- src/components/task-ui.test.tsx
exit=1
Cannot find module '/src/components/task-create-form'
```

GREEN focado e completo após a implementação:

```text
pnpm test -- src/lib/nexo-api.test.ts src/lib/write-policy.test.ts \
  src/app/tarefas/actions.test.ts src/components/task-ui.test.tsx
21 arquivos, 93 testes passaram.

pnpm test
21 arquivos, 93 testes passaram.

pnpm lint
exit=0

pnpm typecheck
next typegen e tsc --noEmit concluíram com exit=0.

pnpm build
exit=0; Next.js 16.3.2 compilou e publicou `/tarefas` como rota dinâmica.

git diff --check
exit=0
```

RED/GREEN adicional dos gates de ferramenta:

- O primeiro lint recusou `setState` síncrono dentro de `useEffect`. O UUID
  passou a ser derivado do estado retornado pela ação, e o efeito ficou restrito
  ao reset do formulário confirmado; teste de UI e lint passaram em seguida.
- O primeiro typecheck recusou acesso direto a propriedades de um `object` no
  parser defensivo sob TypeScript 6. O narrowing foi explicitado como
  `Record<string, unknown>`; teste do parser, typecheck e build passaram.

## Auto-revisão

- `createTaskAction()` chama `requireAuthorizedSession()` antes do primeiro
  `formData.get()`. `requestNexoApi()` repete o guard antes de ler configuração
  ou chamar `fetch`, preservando defesa em profundidade e o guard da Tarefa 7.
- O payload enviado é exatamente `id`, `date`, `title` e `category`, com título
  e categoria normalizados. Validação inválida não chega à API.
- Falhas `writes_disabled`, `idempotency_conflict` e falhas inesperadas retornam
  textos curtos sem stack trace, corpo rejeitado, token ou mensagem interna.
- Revalidação acontece somente no caminho de sucesso e nas rotas `/tarefas` e
  `/`. Erro e conflito não invalidam a UI como se a escrita tivesse ocorrido.
- O UUID enviado permanece em `submittedItemId` em validação e falha. O cliente
  só usa `nextItemId` após `status=success`, impedindo troca de ID em retry
  ambíguo e uma submissão duplicada acidental enquanto `pending` está ativo.
- `NEXO_API_TOKEN` é lido somente em `web/src/lib/nexo-api.ts`, marcado
  `server-only`, e enviado em `X-Nexo-Token`. Não é prop, estado ou campo HTML.
- Um build com `NEXO_API_TOKEN=bundle-audit-sentinel-8f16eab7` e a flag de UI
  ativa não encontrou sentinel, nome do token ou nome da URL em `.next/static`.
  O teste de renderização também confirma ausência do segredo no HTML inicial.
- O build final sem `NEXO_WEB_WRITES_ENABLED` e sem `NEXO_API_TOKEN` passou,
  confirmando o comportamento default fechado sem exigir escrita ao vivo.

## Riscos e limites

- Não houve smoke com OAuth, navegador hidratado ou FastAPI real por restrição
  da tarefa. O contrato foi coberto por testes unitários, HTML estático e build.
- O gate de UI é apenas conveniência. Mesmo quando ativado, a sessão Auth.js, o
  token entre servidores e `NEXO_API_WRITES_ENABLED` no FastAPI continuam sendo
  autoridades independentes.
- O UUID sobrevive aos retries do mesmo formulário montado. Um reload manual da
  página cria intencionalmente uma nova intenção, portanto não representa retry
  automático da submissão anterior.
- A validação do browser é complementar; o servidor permanece a autoridade para
  UUID, limites de texto e data ISO.

## Hashes

- Base da Tarefa 8: `633cf2717eb97723d7e8a7dc54d14612c1efae32`
- Implementação: `b3ab7e0faf55e05d53096022b5819402ff262b31`
- SHA-256 `web/package.json`: `9a4425f15fa1659514b4b0b2bba9910ea62f8ed90532483c631e7d0ff9244812`
- SHA-256 `web/pnpm-lock.yaml`: `ffc37b27016739ec9e8283288e354da1f059101aff806b7ccf494c00393d2516`
- SHA-256 `web/src/lib/nexo-api.ts`: `4a971edfe9258d509734f03a0b751a4fbbba3175b8018171345ddb45a1326404`
- SHA-256 `web/src/lib/write-policy.ts`: `591d4570173c17bc6e442425df99badecbcec3002b12e94bca5a1fe594dbd6c1`
- SHA-256 `web/src/app/tarefas/actions.ts`: `2189a5c02871d4b16ed5897f399f9176fccf224434abcc0f744259fa508b2427`
- SHA-256 `web/src/components/task-create-form.tsx`: `8a46f9070d68f41a01805d8b4ff4f4bac8f6a027f326e53e5fc25735937f679f`
- SHA-256 `web/src/components/tasks-workspace.tsx`: `6ea9431f7da8d8986e67001aa6ca5890ce78263db9b16cfb2d5ea87ee39e8528`
- SHA-256 `web/src/app/tarefas/page.tsx`: `059caedec85d34dc0251d6498d797c15b14bead7c6eb4ab9e22999f9729906c8`
