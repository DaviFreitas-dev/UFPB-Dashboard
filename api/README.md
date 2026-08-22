# NEXO API

API somente de leitura para a interface em Next.js. O serviço consulta todas as
abas necessárias ao painel em um único lote, usa cache curto e autentica o
Google Sheets com escopos de leitura.

## Configuração

Use variáveis privadas no ambiente do servidor:

- `NEXO_API_TOKEN`: segredo compartilhado apenas com o servidor Next.js;
- `GSHEETS_SERVICE_ACCOUNT_JSON`: JSON completo da Service Account;
- `NEXO_TIMEZONE`: fuso usado para determinar o dia atual.

Em desenvolvimento, a API também aceita a seção `gsheets` dos secrets locais do
Streamlit. Nenhuma credencial deve ser copiada para arquivos versionados.

## Executar

```bash
python -m pip install -r requirements-api.txt
uvicorn api.main:app --reload
```

O endpoint `GET /v1/dashboard/today` exige o cabeçalho `X-Nexo-Token`. O
endpoint `GET /health` não consulta a planilha e permanece disponível para
monitoramento.
