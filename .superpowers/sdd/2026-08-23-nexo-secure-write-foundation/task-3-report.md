# Relatório da Tarefa 3 — Fronteira segura de mutações da API

## Resumo

- A autenticação entre servidores foi extraída para `api.security`, preservando a comparação em tempo constante e sem registrar tokens.
- `api.mutations` fornece o portão de escrita fechado por padrão, IDs de operação seguros, erros HTTP estáveis e acesso ao lock reentrante compartilhado de XP.
- A aplicação principal instala esse suporte uma única vez. Não foi criado endpoint de tarefa e não houve escrita em Google Sheets.

## Arquivos alterados

- `api/security.py` — dependência reutilizável do token privado entre servidores.
- `api/mutations.py` — portão de escrita, `NexoMutationError`, middleware de ID de operação e lock compartilhado.
- `api/main.py` — uso da dependência extraída e instalação da fronteira de mutações.
- `tests/test_api_mutations.py` — testes do portão, contrato de erro, ID de operação, token e reentrância.
- `tests/test_api_main.py` — cobertura da instalação do middleware na aplicação principal.

## Evidência RED/GREEN

RED, antes da implementação:

```text
python -m pytest tests/test_api_mutations.py -q
exit=2
ModuleNotFoundError: No module named 'api.mutations'
```

GREEN focado:

```text
python -m pytest tests/test_api_mutations.py tests/test_api_main.py -q
21 passed in 0.62s
```

GREEN da suíte completa:

```text
python -m pytest -q
64 passed in 1.20s
```

## Auto-revisão

- O padrão é bloqueado: somente `NEXO_API_WRITES_ENABLED=true` libera uma dependência de escrita.
- O lock retorna exatamente o `RLock` já usado por concessão de XP; futuros endpoints devem autenticar via `require_api_token` e passar pelo portão antes de executar código protegido por esse lock.
- IDs de operação aceitam somente caracteres seguros e comprimento limitado; entradas inválidas recebem UUID novo.
- O contrato de `NexoMutationError` usa `code`, mensagem definida pelo backend e `operationId`, sem detalhes internos.
- O token não é incluído em respostas ou logs; os testes confirmam que o valor de teste não vaza na resposta de falha.
- `git diff --check` não encontrou erros de whitespace. Não houve escrita em Sheets, push, PR, merge ou deploy.

## Riscos e pendências

- A serialização é por processo, conforme a decisão atual de uma única instância escritora. Escala horizontal exigirá lock distribuído antes de habilitar vários escritores.
- A Tarefa 6 deve compor `require_api_token`, `require_api_writes` e `mutation_lock()` nessa ordem ao criar as rotas de escrita.
- As mensagens de mutação deverão continuar sendo construídas com conteúdo seguro; exceções internas não devem ser convertidas diretamente em `NexoMutationError`.

## Hashes

- Base da Tarefa 3: `0cc93513a315c1ec7d39ef6ab643f280043a4d34`
- Implementação: `6fd4cfb`
