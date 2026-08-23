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
- Validação (`422`), conflito (`409`) e falha interna (`503`) usam códigos
  estáveis e `operationId`, sem devolver o conteúdo rejeitado ou a exceção.
- O cache de leitura é invalidado somente depois de `tasks.add()` confirmar a
  operação. Nenhuma credencial, rede ou planilha real foi usada.

## Arquivos

- `api/task_mutations.py` — modelos Pydantic, rota protegida, validação segura,
  composição do lock/domínio/cache e mapeamento de erros.
- `api/main.py` — inclusão única do router de tarefas; rotas GET preservadas.
- `tests/test_api_task_mutations.py` — autenticação ausente/incorreta, gate
  fechado, ordem dos guards, validação, UUID, sucesso, lock, cache, retry,
  conflito e falha interna sanitizada.

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

GREEN focado:

```text
python -m pytest tests/test_api_task_mutations.py -q
10 passed in 0.56s
```

GREEN exigido pelo brief:

```text
python -m pytest tests/test_api_task_mutations.py tests/test_api_mutations.py tests/test_api_main.py tests/test_tasks.py -q
34 passed in 0.67s
```

GREEN completo e verificações adicionais:

```text
python -m pytest -q
88 passed in 1.96s

python -m compileall -q api modules tests
exit=0

python -c "import api.task_mutations; import api.main"
exit=0

git diff --cached --check
exit=0
```

## Auto-revisão

- A ordem observável é token -> gate -> validação/normalização -> lock ->
  `tasks.add()` -> saída do lock -> invalidação do cache. Os testes diferenciam
  `401`, `503` e `422` para detectar regressões nessa sequência.
- O teste de retry usa o `tasks.add()` real com armazenamento em memória e
  confirma uma única chamada de append para dois POSTs iguais.
- O teste de lock confirma que o domínio inteiro executa dentro da seção crítica,
  cobrindo sua janela read/append sem duplicar a lógica da Tarefa 5.
- O router converte apenas seus próprios erros de validação para o envelope de
  mutação; contratos das rotas GET não foram alterados.
- Falhas internas registram somente `operation_id` sanitizado e o tipo da
  exceção. O texto da exceção não aparece nem na resposta nem no log testado.
- `clear_dashboard_cache()` ocorre depois da confirmação do domínio e não há
  acesso direto a `gspread`, novas chamadas de XP ou mudanças de schema.
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

## Hashes

- Base da Tarefa 6: `293853eddbcdb3d4276f0d4ac06afc7156c706e4`
- Commit de implementação: `d1565303168d1fa0519c157dabf69eb4e62f2b84`
- SHA-256 `api/task_mutations.py`: `2d708a42094e6ec00867a3c914f6631063a32fd872fc6c1475650ebfd3351c41`
- SHA-256 `api/main.py`: `c686a9224f98c33d2545a9d71b0afac1cfdc2a38f7e7ce94712da86e7a76e774`
- SHA-256 `tests/test_api_task_mutations.py`: `8c09d8d339ecb95f246821cc7336eeee17f9ca4295c5bb89c507816d95bc7192`
