# Task 4 — Backfill seguro de IDs legados

## Resumo

Foi criado um planejador de backfill idempotente para as abas cujo schema contém
`id`, uma execução que é dry-run por padrão e uma CLI que só encaminha escrita
após `--apply --confirm BACKFILL_IDS`. O módulo não abre a planilha nem escreve
durante a importação. A execução real não foi chamada nesta tarefa.

Após a revisão, o executor passou a consultar somente abas já existentes: uma
aba ausente retorna contagem zero e nunca é criada, tanto em dry-run quanto no
caminho opt-in. A CLI também funciona tanto como arquivo direto quanto como
módulo a partir da raiz do projeto.

## Arquivos

- `modules/id_backfill.py`: identifica abas com `id`, planeja atualizações
  pontuais e chama o escritor em lote somente com `apply=True`.
- `modules/database.py`: expõe `get_existing_worksheet()` para leituras que não
  criam abas nem cabeçalhos.
- `scripts/backfill_missing_ids.py`: limite de decisão da CLI com confirmação
  exata usando `hmac.compare_digest`, com raiz do projeto disponível na
  invocação direta.
- `tests/test_id_backfill.py`: cobertura do planejador, do dry-run, do lote e
  da confirmação, incluindo ausência de criação e as duas formas de CLI.
- `tests/test_database.py`: garante que a consulta de aba existente não cria
  schema quando a aba não existe.

## RED / GREEN

- RED: `python -m pytest tests/test_id_backfill.py -q` falhou durante a coleta
  com `ImportError` porque `modules.id_backfill` não existia.
- GREEN: após a implementação, `python -m pytest tests/test_id_backfill.py -q`
  passou com `7 passed`.
- Verificação final: `python -m compileall -q modules/id_backfill.py
  scripts/backfill_missing_ids.py` e `python -m pytest -q` passaram, com
  `71 passed`.
- RED da correção: `python -m pytest tests/test_id_backfill.py
  tests/test_database.py -q` falhou com três casos esperados: dry-run chamou o
  criador de aba, a CLI direta não encontrou `modules` e faltava uma consulta
  de worksheet sem criação.
- GREEN da correção: a mesma seleção passou com `26 passed`; `python
  scripts/backfill_missing_ids.py --help` e `python -m
  scripts.backfill_missing_ids --help` retornaram código zero.
- Verificação final da correção: `python -m pytest -q` passou com `75 passed`.

## Auto-revisão

- A enumeração começa em 2; o teste verifica que os destinos permanecem `A2`
  e `A4`, sem tocar no ID existente em `A3`.
- Apenas linhas com conteúdo e ID vazio geram atualização; linhas totalmente
  vazias e IDs existentes são preservados.
- As leituras usam `get_existing_worksheet()` e `get(pad_values=True)` por aba;
  uma aba ausente não aciona `add_worksheet`, atualização de cabeçalho nem
  escrita. As atualizações elegíveis continuam consolidadas em uma única chamada
  a `write_values_batch`.
- O escritor em lote existente limpa caches por aba somente depois de a API do
  Google Sheets confirmar a escrita; o backfill não antecipa essa invalidação.
- A CLI não executa `main()` quando importada e o módulo de domínio não toca na
  planilha até `backfill_missing_ids()` ser chamado.

## Riscos e operação futura

- O parâmetro Python `apply=True` é um opt-in programático; a confirmação
  textual reforçada existe no limite operacional da CLI. Não execute contra a
  planilha sem o backup e a revisão das células previstos no desenho aprovado.
- Cabeçalhos incompatíveis interrompem a operação antes de qualquer lote, para
  não deslocar dados legados.
- O dry-run ainda exige acesso de leitura à planilha para identificar abas e
  IDs existentes, mas não cria schema nem grava valores.
- Nenhuma escrita, conexão ou alteração na planilha real foi realizada.

## Hashes

- Base da tarefa: `c4a16bf` (`docs: registrar fronteira segura de mutacoes`).
- Implementação Task 4: `c566eeae1d5f7cf529037fea16b2e9446280a4d0`
  (`feat: preparar preenchimento seguro de ids legados`).
- Correção da revisão: `d2fe831ef6b82cba8b839426b7ea42f5693a8e0d`
  (`fix: manter backfill em dry-run somente leitura`).
