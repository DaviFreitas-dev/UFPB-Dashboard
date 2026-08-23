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

Os endpoints abaixo exigem o cabeçalho `X-Nexo-Token`:

- `GET /v1/dashboard/today`;
- `GET /v1/planning`;
- `GET /v1/routine?date=AAAA-MM-DD`;
- `GET /v1/studies`;
- `GET /v1/personal?date=AAAA-MM-DD`;
- `GET /v1/profile`.

Cada resposta é montada em memória a partir do mesmo lote de leitura das abas.
Os endpoints não criam registros, não concedem XP e não ajustam dados antigos.
`GET /health` não consulta a planilha e permanece disponível para
monitoramento.
