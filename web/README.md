# NEXO Web

Nova interface do NEXO em Next.js e TypeScript. Ela convive com a aplicação
Streamlit durante a migração e não substitui o deploy atual nesta etapa. A
Entrega 2 inclui ações protegidas para tarefas, rotina por data, hábitos,
leitura e atividade física. Elas permanecem desativadas e ocultas por padrão.

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
- `NEXO_WEB_WRITES_ENABLED=false` para manter os controles de escrita ocultos.

`NEXO_WEB_WRITES_ENABLED` é o nome reconhecido pela implementação atual.
`NEXO_MUTATIONS_UI_ENABLED` não ativa recurso algum e não deve ser usado.
Nenhuma dessas variáveis pode receber o prefixo `NEXT_PUBLIC_`, ser enviada ao
navegador ou ser incluída em commits.

## Limites desta etapa

- as doze áreas do NEXO já podem ser consultadas nesta interface;
- tarefas e compromissos por data têm criação, conclusão, reabertura e exclusão;
- hábitos têm cadastro, arquivamento e registro diário, sem gerar logs na leitura;
- livros têm cadastro, atualização de página, conclusão, reabertura e exclusão;
- atividade física tem registro por data/tipo sem duplicar a conclusão ou o XP;
- essas ações continuam bloqueadas pelos gates web e FastAPI; no uso diário,
  as edições permanecem no Streamlit;
- os controles só aparecem com fonte API e `NEXO_WEB_WRITES_ENABLED=true`;
  valor ausente, inválido ou `false` os mantém ocultos;
- registros legados sem identidade segura ficam somente para consulta;
- check-ins da agenda semanal pertencem à Entrega 3 e não são ativados aqui;
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
os dois gates, não faça OAuth real, não envie mutações para uma API
real e não execute backfill apply como parte desta entrega. O eventual corte
segue o runbook conservador em `api/README.md`: parar todas as escritas
Streamlit antes do dry-run definitivo, manter a quiescência durante revisão,
apply e verificação, usar uma única instância/processo escritor e nunca manter
dois escritores ativos ao mesmo tempo.
