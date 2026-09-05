# NEXO API

API de leitura e fundação de mutações bloqueadas por padrão para a interface
Next.js. O serviço consulta as abas necessárias ao painel em lote, usa cache
curto e mantém as credenciais do Google Sheets somente no servidor.

## Configuração

Use variáveis privadas no ambiente do servidor:

- `NEXO_API_TOKEN`: segredo compartilhado apenas com o servidor Next.js;
- `GSHEETS_SERVICE_ACCOUNT_JSON`: JSON completo da Service Account;
- `NEXO_TIMEZONE`: fuso usado para determinar o dia atual;
- `NEXO_API_WRITES_ENABLED`: gate explícito das mutações; use `false` nesta
  entrega. Valor ausente, inválido ou diferente de `true` bloqueia escritas.

Em desenvolvimento, a API também aceita a seção `gsheets` dos secrets locais do
Streamlit. Nenhuma credencial deve ser copiada para arquivos versionados.

## Executar

```bash
python -m pip install -r requirements-api.txt
uvicorn api.main:app --reload
```

O primeiro processo de produção deve ter exatamente um worker:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1
```

Não aumente workers nem instâncias do Render até existir um lock de mutações
distribuído. Nesta fundação, mais de um processo escritor não é seguro.

Os endpoints abaixo exigem o cabeçalho `X-Nexo-Token`:

- `GET /v1/dashboard/today`;
- `GET /v1/planning`;
- `GET /v1/routine?date=AAAA-MM-DD`;
- `GET /v1/studies`;
- `GET /v1/personal?date=AAAA-MM-DD`;
- `GET /v1/profile`.

As rotas pessoais da Entrega 2 exigem simultaneamente o cabeçalho de servidor
`X-Nexo-Token` e `NEXO_API_WRITES_ENABLED=true`. Com o gate ausente ou
`false`, a API devolve `writes_disabled` antes de validar o corpo ou gravar.

| Recurso | Rotas |
| --- | --- |
| Tarefas | `POST /v1/tasks`, `PATCH/DELETE /v1/tasks/{id}` |
| Rotina por data | `POST /v1/routine-items`, `PATCH/DELETE /v1/routine-items/{id}` |
| Hábitos | `POST /v1/habits`, `PATCH /v1/habits/{config_id}` |
| Registro de hábito | `PUT /v1/habit-checkins/{config_id}/{date}` |
| Leitura | `POST /v1/books`, `PATCH/DELETE /v1/books/{id}` |
| Atividade física | `POST /v1/activities` |

Criações recebem um UUID estável, reutilizado em tentativas após falha.
As regras de XP permanecem em Python e usam eventos únicos. Atividades também
são deduplicadas por data e tipo, incluindo chaves de XP antigas. Livros aceitam
progresso, conclusão e reabertura. Os corpos e confirmações estão no OpenAPI.

Leituras de hábitos não criam registros. Linhas antigas sem identidade segura
continuam visíveis, sem controles de alteração por ID. Repetições de atividades
já concluídas sem ID são confirmadas por data/tipo e retornam `id: null`;
atividades pendentes sem ID retornam conflito, sem atualização por posição.
Nenhum backfill foi executado nesta entrega.

`AgendaSemanal` e `AgendaCheckins` permanecem somente leitura; os check-ins
semanais pertencem à Entrega 3. A ativação do novo escritor é uma etapa separada,
prevista para a Entrega 4, não uma consequência de instalar estas rotas.

Cada resposta de leitura é montada em memória a partir do mesmo lote de abas.
`GET /health` não consulta a planilha e permanece disponível para
monitoramento.

## Runbook conservador de rollout e corte

Esta entrega não autoriza um corte. O Streamlit continua sendo o escritor do
dia a dia; mantenha `NEXO_API_WRITES_ENABLED=false` no Render e
`NEXO_WEB_WRITES_ENABLED=false` na Vercel. Esses são gates independentes e
devem começar fechados. O formulário web fica oculto com o gate da interface
fechado, e o gate da API continua recusando qualquer tentativa de escrita.

Antes de qualquer corte futuro, execute manualmente, com revisão humana:

1. Confirme `NEXO_API_WRITES_ENABLED=false` e
   `NEXO_WEB_WRITES_ENABLED=false`, escolha uma janela curta de manutenção e
   confirme que o Streamlit ainda é o único escritor em uso.
2. Entre em manutenção e pare **todas** as escritas Streamlit antes do dry-run
   definitivo. Interrompa o aplicativo ou use um mecanismo que impeça todos os
   fluxos de mutação; confirme que o caminho antigo já não consegue gravar.
3. Aguarde requisições em andamento e pelo menos o maior TTL de cache atual
   (15 segundos). Confirme que não existe nenhum processo escritor ativo.
4. Faça um backup verificável da planilha já em quiescência.
5. Ainda em quiescência, gere e persista o plano definitivo, sem escrita:
   `python scripts/backfill_missing_ids.py --plan-out reviewed-backfill-plan.json`.
6. Revise o console e o JSON: estado de cada aba, linha, célula e UUID exato.
   Mantenha o Streamlit parado. Se qualquer dado mudar, descarte o plano e
   recomece a partir de um novo dry-run em quiescência.
7. Depois da revisão humana explícita, aplique exatamente o arquivo revisado:
   `python scripts/backfill_missing_ids.py --apply-plan reviewed-backfill-plan.json --confirm BACKFILL_IDS`.
8. Sem sair da manutenção, verifique cabeçalhos, células alteradas, UUIDs e
   contagens. Os gates FastAPI e web devem continuar fechados até o fim dessa
   verificação.
9. A ativação de `NEXO_API_WRITES_ENABLED` e, depois, de
   `NEXO_WEB_WRITES_ENABLED` pertence a uma decisão de corte separada e
   posterior. Nunca deixe Streamlit e FastAPI como escritores ao mesmo tempo.

Os comandos acima são instruções operacionais: este README não executa
backfill, OAuth, chamadas à planilha nem mudanças de configuração. Em caso de
falha relevante, feche primeiro o gate da API, aguarde requisições e cache,
confirme que não há operação pendente e só então restaure o escritor Streamlit.
