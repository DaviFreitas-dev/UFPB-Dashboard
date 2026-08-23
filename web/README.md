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

- as doze áreas do NEXO já podem ser consultadas nesta interface;
- todas as telas em Next.js são somente leitura;
- cadastros, conclusões e demais edições continuam no Streamlit;
- nenhuma credencial do Google Sheets pertence ao frontend;
- a troca do aplicativo publicado só deve acontecer depois de existir um único
  caminho seguro para gravações e XP;
- os contratos da API ficam agrupados em `src/lib/dashboard.ts`,
  `src/lib/planning.ts`, `src/lib/routine.ts`, `src/lib/study-workspace.ts`,
  `src/lib/personal-workspace.ts` e `src/lib/profile-workspace.ts`.

## Verificações

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```
