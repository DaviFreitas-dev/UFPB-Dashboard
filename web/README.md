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

## Login GitHub e variáveis privadas

O login GitHub protege o aplicativo pessoal publicado na internet; ele não é
um login para editar o repositório GitHub. Configure o OAuth com este callback:

- local: `http://localhost:3000/api/auth/callback/github`;
- Vercel: `https://<dominio>/api/auth/callback/github`.

Na Vercel, configure somente como segredos privados de servidor:

- `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET` e `AUTH_SECRET` para Auth.js;
- `NEXO_ALLOWED_GITHUB_ID`, que deve ser o ID numérico imutável da conta
  autorizada, e não o login/nome de usuário;
- `NEXO_API_URL` e `NEXO_API_TOKEN` para a comunicação servidor-a-servidor com
  a API;
- `NEXO_WEB_WRITES_ENABLED=false` para manter o formulário de tarefa oculto.

`NEXO_WEB_WRITES_ENABLED` é o nome reconhecido pela implementação atual.
`NEXO_MUTATIONS_UI_ENABLED` não ativa recurso algum e não deve ser usado.
Nenhuma dessas variáveis pode receber o prefixo `NEXT_PUBLIC_`, ser enviada ao
navegador ou ser incluída em commits.

## Limites desta etapa

- as doze áreas do NEXO já podem ser consultadas nesta interface;
- todas as telas em Next.js são somente leitura;
- cadastros, conclusões e demais edições continuam no Streamlit;
- o formulário de criação de tarefa só é renderizado quando a fonte é a API e
  `NEXO_WEB_WRITES_ENABLED=true`; ausente, inválida ou `false` o mantém oculto;
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

## Operação segura nesta entrega

Mantenha `NEXO_WEB_WRITES_ENABLED=false` e `NEXO_API_WRITES_ENABLED=false` em
produção durante esta entrega. O Streamlit continua como escritor; não habilite
os dois gates, não faça OAuth real, não envie `POST /v1/tasks` para uma API
real e não execute backfill apply como parte desta fundação. O eventual corte
segue o runbook conservador em `api/README.md`: backup e revisão, dry-run antes
de apply com a confirmação exata, uma única instância/processo escritor e
nunca dois escritores ativos ao mesmo tempo.
