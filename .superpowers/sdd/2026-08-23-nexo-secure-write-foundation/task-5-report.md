# Tarefa 5 — criação idempotente de tarefas

## Resumo

`modules.tasks.add()` agora aceita um `item_id` estável e retorna `(record, created)`.
Uma repetição com o mesmo ID e os mesmos campos imutáveis retorna a tarefa já
persistida sem adicionar linha. O mesmo ID com data, texto ou categoria diferentes
gera `TaskIdConflict`. Chamadas atuais do Streamlit continuam válidas porque
`item_id` é opcional e o retorno pode ser ignorado.

## Arquivos

- `modules/tasks.py`: `TaskIdConflict` e criação idempotente por ID.
- `tests/test_tasks.py`: criação com ID estável, retry sem append e conflito.

## RED / GREEN

- RED: `python -m pytest tests/test_tasks.py -q` retornou `3 failed`; as causas
  foram `add()` sem `item_id` e ausência de `TaskIdConflict`.
- GREEN focal: `python -m pytest tests/test_tasks.py tests/test_gamification.py -q`
  retornou `9 passed`.
- GREEN completo: `python -m pytest -q` retornou `78 passed`.
- Verificações adicionais: `python -m compileall -q modules tests` e
  `git diff --check` retornaram código de saída zero.

O teste de retry impede um segundo `append_record`. A suíte de gamificação já
verifica duas chamadas com a mesma `event_key` e também a repetição concorrente,
confirmando uma única escrita de XP; `toggle()` continua usando
`event_key=f"task:{item_id}"` sem mudança.

## Auto-revisão

- O domínio usa apenas `records()` e `append_record()` importados de
  `modules.database`; não foi introduzido acesso direto a `gspread`.
- Apenas `id`, `data`, `tarefa` e `categoria` participam da comparação de retry.
  Um status já alterado é preservado quando a criação é repetida.
- Dados lidos continuam defensivos via `row.get()`.
- O diff não contém segredos nem alterações no fluxo de XP.

## Riscos e limites

- A deduplicação de criação cobre a repetição observada pelo domínio. Duas
  requisições que atravessem a leitura antes de qualquer `append_record` ainda
  exigiriam serialização/condição atômica no armazenamento para garantia entre
  processos; isso não faz parte do brief desta tarefa.
- O comportamento novo depende de o cliente reutilizar o mesmo UUID nas tentativas.
  Chamadas legadas sem `item_id` continuam gerando um ID novo, como antes.

## Hashes

- Base: `d0b420d51051b287eea3bef0088ff02798714105`
- Commit de implementação: `5709a3808986e2cb9fd32fe36460ee2889a1c21f`
- SHA-256 `modules/tasks.py`: `5b618582862accfab3d69bcef1ce2b5e1471b2047a47c448928cec8ae4bc6f54`
- SHA-256 `tests/test_tasks.py`: `7902854581f8354f74223237325f38f68de09ffc2a5b3a1d45c335c3e08be46c`
