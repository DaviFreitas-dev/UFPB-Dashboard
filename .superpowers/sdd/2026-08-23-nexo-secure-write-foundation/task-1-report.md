# Relatório da Tarefa 1 — Fundação compartilhada e segura de credenciais

## Resumo

Foi criada a fronteira compartilhada de credenciais do Google Sheets. O loader prioriza `GSHEETS_SERVICE_ACCOUNT_JSON`, valida JSON e objeto-raiz, e usa como fallback a seção atual `gsheets` do Streamlit. A API de leitura passou a consumir `READ_ONLY_SCOPES` e `load_service_account_info()` do módulo compartilhado. Também foram expostos os scopes de leitura e leitura-escrita para consumo posterior pela Tarefa 2.

## Arquivos alterados

- `modules/sheets_credentials.py` — novo loader e contratos `READ_ONLY_SCOPES`/`READ_WRITE_SCOPES`.
- `api/sheets.py` — remoção do resolver local e uso do loader compartilhado.
- `tests/test_sheets_credentials.py` — testes de prioridade do ambiente, JSON inválido e fallback Streamlit.
- `tests/test_api_sheets.py` — validação do símbolo público de scopes.

## Evidência RED/GREEN

RED, antes da implementação:

```text
python -m pytest tests/test_sheets_credentials.py -q
exit=1
ImportError: cannot import name 'sheets_credentials' from 'modules'
```

GREEN focado:

```text
python -m pytest tests/test_sheets_credentials.py tests/test_api_sheets.py -q
6 passed in 0.24s
```

GREEN da suíte completa e compilação:

```text
python -m pytest -q
54 passed in 1.02s

python -m compileall -q api modules tests
exit=0
```

## Auto-revisão

- Não foram adicionados valores de secrets, tokens ou chaves privadas.
- Os nomes existentes (`GSHEETS_SERVICE_ACCOUNT_JSON` e `gsheets`) foram preservados.
- A API continua usando somente scopes read-only.
- O fallback Streamlit permanece lazy e isolado no módulo compartilhado.
- `git diff --check` não encontrou erro de whitespace.
- Não houve chamada ao Google Sheets real, push, PR, merge ou deploy.

## Riscos e pendências

- A Tarefa 2 ainda precisa consumir `READ_WRITE_SCOPES` e o mesmo loader na camada de banco.
- A disponibilidade das credenciais reais continua sendo responsabilidade da configuração privada de cada ambiente.
- O contrato não valida campos internos da Service Account; a validação fica para a biblioteca Google Auth no momento da abertura.

## Hash do commit

Commit da implementação da Tarefa 1: `4cd727da20abdc7eee25fec4e65ce392fe8652b1`
