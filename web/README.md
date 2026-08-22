# NEXO Web

Nova interface do NEXO em Next.js e TypeScript. Ela convive com a aplicação
Streamlit durante a migração e não substitui o deploy atual nesta etapa.

## Executar

```bash
pnpm install
pnpm dev
```

A aplicação usa dados de demonstração enquanto `NEXO_API_URL` não estiver
definida. Quando a API Python estiver disponível, copie `.env.example` para
`.env.local`, ajuste o endereço e use o mesmo `NEXO_API_TOKEN` configurado no
servidor da API. Essas variáveis são lidas apenas no servidor Next.js.

## Limites desta etapa

- a tela Hoje é somente leitura;
- as outras áreas continuam no Streamlit;
- nenhuma credencial do Google Sheets pertence ao frontend;
- o contrato esperado da API está em `src/lib/dashboard.ts`.

## Verificações

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
