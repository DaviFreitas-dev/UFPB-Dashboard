# Task 2 — Runtime-independent database cache

## Resumo

- A camada `modules.database` deixou de importar ou depender diretamente do runtime do Streamlit.
- A conexão e o índice de abas agora usam caches Python `lru_cache`; as linhas usam uma cache própria de 15 segundos, protegida por `RLock` e com cópias profundas para impedir mutação acidental pelo chamador.
- `connect_sheet()` passou a reutilizar `load_service_account_info()` e `READ_WRITE_SCOPES` da Tarefa 1.
- `clear_records_cache(name=None)` preserva o contrato público, e `clear_resource_caches()` foi adicionado para testes e ciclo de vida do processo.
- `initialize_database()` agora é cacheável com `lru_cache` e sua limpeza ocorre somente após a função já estar definida.

## Arquivos alterados

- `modules/database.py`
- `tests/test_database.py`

## Evidência RED

1. Após adicionar os testes de contrato e antes da refatoração:

   ```text
   python -m pytest tests/test_database.py -q
   1 failed, 13 passed
   FAILED test_database_module_has_no_top_level_streamlit_dependency
   AssertionError: "import streamlit as st" ainda estava presente
   ```

2. Após adicionar o teste da limpeza pública e remover temporariamente sua implementação:

   ```text
   python -m pytest tests/test_database.py -q
   1 failed, 14 passed
   FAILED test_clear_resource_caches_resets_connection_worksheet_and_records_caches
   AttributeError: module 'modules.database' has no attribute 'clear_resource_caches'
   ```

## Evidência GREEN e verificação

```text
python -m pytest tests/test_database.py -q
15 passed in 0.28s

python -m pytest tests/test_database.py tests/test_gamification.py tests/test_study_sessions.py -q
25 passed in 0.36s

python -m compileall -q modules api views
exit 0

python -c "import modules.database; print('modules.database imported without Streamlit context')"
modules.database imported without Streamlit context

git diff --check
exit 0
```

## Auto-revisão

- O módulo não contém `import streamlit as st` nem decoradores `@st.cache_`.
- A criação de uma aba ausente continua serializada pelo mesmo bloqueio reentrante usado pela cache de registros.
- As escritas existentes continuam invalidando apenas a cache da aba afetada após confirmação da API.
- A cache de registros mantém TTL de 15 segundos e devolve cópias profundas tanto no preenchimento quanto na reutilização.
- Não houve leitura ou escrita em Google Sheets real, nem alteração de segredos.

## Riscos e limites

- Os caches são por processo; múltiplos processos não compartilham invalidação. Isso é compatível com a restrição atual da primeira versão da API a uma instância/processo escritor.
- `clear_resource_caches()` deve ficar restrito a testes e ao ciclo de vida do processo, pois ele descarta conexões e o resultado da inicialização cacheada.
- Os avisos locais de conversão LF para CRLF foram emitidos pelo Git, sem erro de diff ou alteração semântica.

## Hashes

- `31b7c0e8ca22fb5a6c875df807e2ba463fae3a0c` — `refactor: desacoplar banco do contexto Streamlit`
