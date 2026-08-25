# NEXO secure-write foundation — relatório da onda final de correções

**Data:** 25 de agosto de 2026

**Base original da onda:** `d8d0a8aa1a08488ce08c53babf78ddcc873cd301`

**Snapshot verificado antes deste relatório:** `c97639e3fbbfb0c7d3d07833d4678647591a068b`
**Escopo:** uma única onda final, sem OAuth, Google Sheets real, backfill apply
real, deploy, push, PR ou merge.

## Resultado

Os quatro findings Important foram corrigidos e verificados. Os dois primeiros
commits herdados foram auditados antes das correções restantes. Os três findings
Minor foram tratados; o teste hidratado real não foi adicionado porque o harness
não possui ambiente DOM e a própria finding permitia registrar essa limitação
quando a alternativa exigisse dependências/churn. Os testes reais já existentes
de Server Action, estado e renderização estática foram mantidos sem serem
reclassificados como teste hidratado.

O Streamlit continua sendo o escritor operacional. Os gates FastAPI e web
continuam fechados por padrão. Nenhuma ação operacional real foi executada.

## Auditoria dos commits herdados

### `3c9530bc36cce36b8fe5b94cadd731fb874f24eb`

Finding coberta: **Important #1 — plano revisável de backfill**.

Auditoria do diff e do código atual:

- o dry-run distingue aba ausente de aba presente sem IDs pendentes;
- o plano JSON persiste aba, estado, cabeçalho esperado, linha one-based,
  célula e UUID v4 canônico exato;
- o apply consome o arquivo revisado, não replana UUIDs;
- todas as abas e precondições são revalidadas antes de uma única gravação em
  lote;
- cabeçalho, existência da linha, célula de ID vazia e linha ainda não vazia
  são conferidos novamente;
- planos com campos extras, UUID inválido, célula duplicada ou estado
  incompatível são recusados;
- nenhuma aba é criada pelo dry-run ou apply;
- a CLI real suporta `--plan-out` e `--apply-plan ... --confirm BACKFILL_IDS`.

Verificação herdada repetida: `python -m pytest tests/test_id_backfill.py -q`
resultou em **18 passed**. Nenhuma correção adicional foi necessária nesse
commit.

### `215d04a6767baf1e3969691674358818985c9760`

Finding coberta: **Important #3 — validação da resposta web confirmada**.

Auditoria do diff e do código atual:

- `requestNexoApi` exige um schema Zod explícito para respostas 2xx;
- o contrato estrito exige `operationId`, `created` e a tarefa completa;
- `{}`, JSON de erro com status 2xx, JSON inválido e campos extras/divergentes
  são tratados como resposta ambígua sanitizada;
- a Server Action confere ID, data, título e categoria retornados contra a
  solicitação normalizada;
- `created=true` e `created=false` são confirmações válidas;
- em falha ambígua, o UUID enviado é preservado, não há revalidação de página
  nem rotação para um novo UUID.

Verificação herdada repetida e depois focada: a suíte web existente passou
**108/108**; `pnpm exec vitest run src/lib/nexo-api.test.ts
src/app/tarefas/actions.test.ts` passou **28/28**. Nenhuma correção adicional
foi necessária nesse commit.

## Findings e status final

| Finding | Status | Evidência principal |
| --- | --- | --- |
| Important #1 — plano de backfill revisável | Concluído/auditado | Commit `3c9530b`; 18/18 testes herdados e 39/39 focados finais com a API |
| Important #2 — quiescência antes do dry-run definitivo | Concluído | Spec e runbook agora param todas as escritas Streamlit antes do plano definitivo e mantêm os dois gates fechados durante gerar/revisar/aplicar/verificar |
| Important #3 — validar resposta 2xx web | Concluído/auditado | Commit `215d04a`; schema Zod estrito, comparação da tarefa e 28/28 focados web |
| Important #4 — observabilidade estruturada segura | Concluído | Eventos JSON `create`, `replay`, `conflict`, `failure`; RED/GREEN e caplog com redaction |
| Minor #1 — flag web canônica | Concluído | Errata explícita na spec/plano; orientação operacional usa `NEXO_WEB_WRITES_ENABLED`; nome antigo aparece apenas como obsoleto |
| Minor #2 — wording de mutações protegidas | Concluído | Metadata FastAPI e README web declaram mutações protegidas, fechadas por padrão |
| Minor #3 — comportamento hidratado | Limite permitido e documentado | Tentativa real falhou antes dos testes por ausência de `jsdom`; nenhuma pilha nova nem teste estático falsamente rotulado |

## Important #2 — sequência canônica sem ação real

Spec e `api/README.md` agora determinam, para uma entrega futura aprovada:

1. confirmar `NEXO_API_WRITES_ENABLED=false` e
   `NEXO_WEB_WRITES_ENABLED=false`;
2. entrar em manutenção e parar todos os caminhos de escrita Streamlit;
3. confirmar que o fluxo antigo não grava, aguardar requisições e o TTL máximo
   atual de 15 segundos;
4. fazer backup verificável já em quiescência;
5. gerar o plano definitivo com `--plan-out`;
6. revisar aba, estado, linha, célula e UUID mantendo a quiescência;
7. aplicar o mesmo arquivo com `--apply-plan ... --confirm BACKFILL_IDS`;
8. verificar cabeçalhos, células, UUIDs e contagens ainda em manutenção;
9. manter os gates FastAPI/web fechados até o fim dessa verificação e tratar a
   ativação como decisão posterior separada.

Este relatório e os testes não executaram nenhum desses passos contra sistemas
reais.

## Important #4 — RED/GREEN

### RED

Depois de adicionar primeiro os testes de contrato de log:

```text
python -m pytest tests/test_api_task_mutations.py -q
4 failed, 17 passed
```

As quatro falhas foram as esperadas: nenhum evento estruturado existia para
create, replay ou conflict, e o failure ainda usava uma mensagem genérica.

### GREEN

Após a implementação mínima:

```text
python -m pytest tests/test_api_task_mutations.py -q
21 passed

python -m pytest tests/test_api_task_mutations.py tests/test_api_mutations.py tests/test_api_main.py tests/test_tasks.py -q
45 passed
```

Cada evento JSON contém somente:

- timestamp UTC;
- `operation_id` e `request_id` correlacionados;
- rota `/v1/tasks`;
- duração em milissegundos;
- `task_uuid` depois da validação;
- outcome, status e worksheet `Tarefas`.

Os testes caplog verificam ausência de token, título, categoria, payload e texto
privado da exceção. O logger não recebe `exc_info` nem argumentos contendo esses
valores.

## Minor #3 — tentativa de teste hidratado

Infraestrutura encontrada:

- Vitest configurado com `environment: "node"`;
- nenhuma dependência instalada de `jsdom`, `happy-dom`, Testing Library,
  Playwright ou `react-test-renderer`;
- os arquivos do Next.js que mencionam Playwright são código interno/documentação
  do framework, não o runner instalado no projeto.

Tentativa concreta:

```text
pnpm exec vitest run src/components/task-ui.test.tsx --environment jsdom
MISSING DEPENDENCY  Cannot find dependency 'jsdom'
Test Files  no tests
Tests       no tests
Errors      1 error
```

Adicionar jsdom + Testing Library alteraria manifest, lockfile, configuração e
modelo de testes apenas para esta finding. Isso é o churn amplo que a finding
mandou evitar. Permaneceram os testes reais de Server Action para erro ambíguo,
retry com o mesmo UUID, replay/sucesso, revalidação e UUID novo, além do teste
puro de transição do ID e da renderização estática acessível. O estado pending
continua desabilitando campos e botão no componente, mas pending/duplo envio não
foi apresentado como coberto por um teste hidratado inexistente.

## Verificação completa

Todos os comandos abaixo foram executados no worktree indicado, sem rede ou
credenciais reais.

### Python

```text
python -m pytest -q
108 passed in 5.48s

python -m compileall -q app.py modules api views scripts
exit 0; sem saída

python -c "import api.main; import api.task_mutations; import modules.database; import modules.id_backfill; import scripts.backfill_missing_ids; print('focused imports: ok')"
focused imports: ok
```

Focados finais:

```text
python -m pytest tests/test_id_backfill.py tests/test_api_task_mutations.py -q
39 passed in 2.65s
```

### Web

O PATH recebeu os dois diretórios de runtime informados antes de cada comando.

```text
pnpm test
21 test files passed; 108 tests passed

pnpm lint
exit 0; sem erros

pnpm typecheck
route types gerados; TypeScript exit 0

pnpm build
Next.js 16.3.2 compilou, tipou, gerou as páginas e finalizou com exit 0
```

O script de build executou também `pnpm test:build-artifacts`:

```text
2 tests; 2 passed; 0 failed
```

Focados finais:

```text
pnpm exec vitest run src/lib/nexo-api.test.ts src/app/tarefas/actions.test.ts
2 test files passed; 28 tests passed
```

### Integridade e segredos

```text
git diff --check
exit 0

git diff --check d8d0a8aa1a08488ce08c53babf78ddcc873cd301..HEAD
exit 0

git grep -n -I -E 'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|private_key_id|ghp_[A-Za-z0-9]|github_pat_' -- . ':!docs/superpowers/plans/*'
sem matches

git ls-files | rg '(^|/)(\.env($|\.(local|production|development))|secrets\.toml)$'
nenhum arquivo runtime sensível versionado

git status --short
limpo antes da criação deste relatório
```

## Arquivos da onda final

### Herdados e auditados

- `modules/id_backfill.py`
- `scripts/backfill_missing_ids.py`
- `tests/test_id_backfill.py`
- `web/src/lib/task-mutation-contract.ts`
- `web/src/lib/nexo-api.ts`
- `web/src/lib/nexo-api.test.ts`
- `web/src/app/tarefas/actions.ts`
- `web/src/app/tarefas/actions.test.ts`

### Corrigidos nesta retomada

- `api/task_mutations.py`
- `tests/test_api_task_mutations.py`
- `api/main.py`
- `api/README.md`
- `web/README.md`
- `docs/superpowers/specs/2026-08-23-nexo-write-migration-design.md`
- `docs/superpowers/plans/2026-08-23-nexo-secure-write-foundation.md`
- `.superpowers/sdd/2026-08-23-nexo-secure-write-foundation/final-fix-report.md`

## Auto-revisão

- O fluxo aceito token -> gate -> validação -> lock continua preservado.
- O UUID validado continua estável em retry e respostas ambíguas.
- O cache só é limpo depois do resultado de domínio; replays continuam seguros.
- Os logs não serializam o payload nem interpolam texto de exceção.
- O backfill continua dry-run por padrão, usa somente lookup de abas existentes
  e grava apenas o plano revisado depois de revalidar todas as precondições.
- A documentação não sugere mais dry-run definitivo enquanto o Streamlit ainda
  escreve.
- `NEXO_MUTATIONS_UI_ENABLED` aparece somente em errata que o marca como
  obsoleto; toda orientação operacional usa `NEXO_WEB_WRITES_ENABLED`.
- FastAPI e web continuam desativados por padrão nos exemplos e no código.
- Não foram adicionadas dependências nem alterações fora do escopo.

## Limites e concerns residuais

- Não existe teste hidratado/DOM no harness atual; a lacuna e a tentativa
  concreta estão registradas acima.
- OAuth real, Google Sheets real, aplicação do backfill, deploy e corte não
  foram exercitados por restrição explícita.
- O lock de mutação permanece local ao processo; produção deve continuar com
  um worker/uma instância até existir lock distribuído.
- Parar todas as escritas Streamlit é uma etapa operacional futura e precisa de
  confirmação humana; este branch apenas corrige o runbook.

## Commits da onda

- base: `d8d0a8aa1a08488ce08c53babf78ddcc873cd301`
- backfill herdado/auditado: `3c9530bc36cce36b8fe5b94cadd731fb874f24eb`
- resposta web herdada/auditada: `215d04a6767baf1e3969691674358818985c9760`
- logs estruturados seguros: `f1312a492b1d5317032598e428488b42c9671839`
  (`feat(api): registrar mutacoes de tarefas com seguranca`)
- runbook, errata e metadata: `c97639e3fbbfb0c7d3d07833d4678647591a068b`
  (`docs: corrigir runbook de corte e gates`)

O hash final do commit que adiciona este próprio relatório deve ser obtido por
`git rev-parse HEAD`; um commit não pode conter de forma estável o próprio hash.
