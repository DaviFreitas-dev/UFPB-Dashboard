# Relatório da Tarefa 6 — primeiro POST protegido de tarefas

## Resumo

- `POST /v1/tasks` foi registrado uma única vez no FastAPI e exige o token
  privado entre servidores e `NEXO_API_WRITES_ENABLED=true`.
- A rota normaliza e valida o payload tipado antes de entrar no lock reentrante
  compartilhado. Toda a chamada idempotente a `modules.tasks.add()` — incluindo
  sua leitura e seu append — ocorre dentro do lock.
- O UUID fornecido pelo cliente é reutilizado como ID persistente. Um retry
  idêntico devolve a mesma tarefa com `created=false`, sem segunda linha; a
  reutilização do UUID com outro conteúdo devolve conflito `409` sanitizado.
- Autenticação (`401`/`503`), gate (`503`), validação (`422`), conflito (`409`)
  e falha interna (`503`) usam o mesmo envelope com código estável e
  `operationId`, sem devolver conteúdo rejeitado ou exceções.
- O JSON só é decodificado depois de token e gate válidos. O OpenAPI publica o
  request real e `MutationErrorResponse`, sem anunciar `HTTPValidationError`.
- O cache de records é limpo antes e depois de toda tentativa de append,
  inclusive quando a resposta se perde depois da persistência. O cache do
  dashboard continua sendo invalidado apenas depois da confirmação do domínio.
- Leituras preservam valores textuais exatos como `"001"`, sem numericise local.
  Nenhuma credencial, rede ou planilha real foi usada.

## Arquivos

- `api/task_mutations.py` — modelos Pydantic, rota protegida, validação segura,
  composição do lock/domínio/cache e mapeamento de erros.
- `api/main.py` — inclusão única do router de tarefas; rotas GET preservadas.
- `modules/database.py` — leitura textual e invalidação de cache segura em
  sucesso ou falha ambígua de append.
- `tests/test_api_task_mutations.py` — autenticação ausente/incorreta, gate
  fechado, ordem dos guards, validação, UUID, sucesso, lock, cache, retry,
  conflito, falha interna sanitizada, JSON truncado e OpenAPI.
- `tests/test_database.py` — regressão da preservação do texto `"001"`.

## RED / GREEN

RED inicial, antes da implementação:

```text
python -m pytest tests/test_api_task_mutations.py -q
exit=1
ModuleNotFoundError: No module named 'api.task_mutations'
```

RED da rota, depois de criar apenas o módulo de composição:

```text
python -m pytest tests/test_api_task_mutations.py -q
exit=1
10 failed; todas as respostas eram 404 porque POST /v1/tasks não existia
```

RED do contrato de validação sanitizado:

```text
python -m pytest tests/test_api_task_mutations.py -q -k "empty_title or stable_uuid"
exit=1
2 failed; o 422 padrão não possuía error.code=invalid_request
```

RED da revisão — append persistido com resposta perdida:

```text
python -m pytest tests/test_api_task_mutations.py -q -k "response_is_lost"
exit=1
retry retornou created=true porque records() reutilizou o cache anterior ao append
```

RED da revisão — texto numérico:

```text
python -m pytest tests/test_database.py -q -k "numeric_looking"
exit=1
esperado "001"; recebido 1
```

RED da revisão — guards, envelopes e OpenAPI:

```text
python -m pytest tests/test_api_task_mutations.py -q
exit=1
6 failed: auth usava detail; JSON truncado retornava 422 antes dos guards;
OpenAPI referenciava HTTPValidationError
```

GREEN focado:

```text
python -m pytest tests/test_api_task_mutations.py tests/test_api_mutations.py tests/test_api_main.py tests/test_tasks.py tests/test_database.py -q
60 passed in 0.87s
```

GREEN completo e verificações adicionais:

```text
python -m pytest -q
98 passed in 2.00s

python -m compileall -q api modules tests
exit=0

python -c "import api.task_mutations; import api.main; import modules.database"
exit=0

git diff --cached --check
exit=0
```

## Auto-revisão

- A ordem observável é token -> gate -> validação/normalização -> lock ->
  `tasks.add()` -> saída do lock -> invalidação do cache. Os testes diferenciam
  `401`, `503` e `422` inclusive com JSON truncado, detectando regressões nessa
  sequência antes da decodificação do body.
- Os testes de retry usam `tasks.add()` e `database.records()` reais com uma
  worksheet falsa. Eles confirmam uma única chamada de append quando a linha é
  persistida mas a resposta do append se perde, e também quando a invalidação do
  dashboard falha depois da persistência.
- O teste de lock confirma que o domínio inteiro executa dentro da seção crítica,
  cobrindo sua janela read/append sem duplicar a lógica da Tarefa 5.
- O router converte seus erros de autenticação e validação para o envelope de
  mutação. `api.security` e os contratos das rotas GET não foram alterados.
- O OpenAPI contém uma única operação `POST /v1/tasks`, request com UUID/data e
  erro 422 tipado como `MutationErrorResponse`.
- `modules.database` não numericiza mais registros lidos. A suíte completa prova
  compatibilidade dos consumidores que já convertem números explicitamente.
- Falhas internas registram somente `operation_id` sanitizado e o tipo da
  exceção. O texto da exceção não aparece nem na resposta nem no log testado.
- Caminhos sem persistência — auth, gate, validação e conflito — não invalidam o
  cache do dashboard. Não há novas chamadas de XP ou mudanças de schema.
- A busca nos arquivos alterados encontrou somente tokens e segredos fictícios
  dos testes. Não houve push, PR, merge, deploy ou escrita em Sheets.

## Riscos e pendências

- `mutation_lock()` continua sendo local ao processo. A garantia pressupõe a
  única instância/processo escritor definida no desenho; escala horizontal
  exigirá lock distribuído ou outro armazenamento.
- `clear_dashboard_cache()` invalida hoje o cache agregado do painel, não apenas
  a aba `Tarefas`. Isso preserva o primitive existente, mas pode ser refinado em
  uma etapa futura sem mudar o contrato desta rota.
- Se o cache falhar depois de uma gravação confirmada, a resposta é `write_failed`;
  o retry com o mesmo UUID permanece seguro e recupera a tarefa existente.
- A leitura sem numericise entrega números do Sheets como strings; consumidores
  numéricos continuam responsáveis pelas conversões defensivas já existentes.

## Hashes

- Base da Tarefa 6: `293853eddbcdb3d4276f0d4ac06afc7156c706e4`
- Implementação inicial: `d1565303168d1fa0519c157dabf69eb4e62f2b84`
- Correções da revisão: `a78da92237309ba6abc2b022d4c474d999d50f25`
- SHA-256 `api/task_mutations.py`: `cf4ec73550dd93575355882189a40e7374c2ff1016f86b3c7063f019e752d3ee`
- SHA-256 `api/main.py`: `c686a9224f98c33d2545a9d71b0afac1cfdc2a38f7e7ce94712da86e7a76e774`
- SHA-256 `modules/database.py`: `2af318e1d31081b374da72e80e6a9c2384b5ec12a4a72b60575c8bc20814f1ec`
- SHA-256 `tests/test_api_task_mutations.py`: `402c999c386abae2926000332f0b638f7a0bc5f0cd6444d8ee3eb6f8fd3b9161`
- SHA-256 `tests/test_database.py`: `65253d2a1d6043c64d3eb31028009fa2bb9f3204e18366c7af99aebcfd8a6e70`
