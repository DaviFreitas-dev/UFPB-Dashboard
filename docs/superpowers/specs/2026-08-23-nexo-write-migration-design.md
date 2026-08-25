# NEXO — Migração segura das escritas para a interface Next.js

**Data:** 23 de agosto de 2026

**Status:** desenho aprovado em conversa; aguardando revisão deste documento

**Escopo:** autenticação, operações de escrita, experiência de edição e corte do Streamlit para a nova interface

## Errata canônica da fundação

A implementação desta entrega usa `NEXO_WEB_WRITES_ENABLED` como gate privado
do formulário web. O nome anterior `NEXO_MUTATIONS_UI_ENABLED` está obsoleto,
não ativa nenhum recurso e não deve aparecer em configuração ou orientação
operacional. Este erratum prevalece sobre referências históricas ao nome
anterior.

A fundação já contém uma mutação protegida (`POST /v1/tasks`), mas os gates web
e FastAPI permanecem fechados por padrão. Portanto, “somente leitura” nesta
entrega descreve o estado operacional com os gates fechados, não a ausência de
rotas ou componentes de mutação.

## 1. Contexto

O NEXO possui uma aplicação Streamlit funcional, uma interface Next.js com as 12 áreas do produto em modo de leitura e uma API FastAPI que consulta o Google Sheets. A próxima etapa é permitir que a nova interface também altere os dados, sem comprometer o histórico, a deduplicação de XP ou a possibilidade de voltar temporariamente ao Streamlit.

A migração é arquitetural porque muda o responsável pelas escritas e cria uma nova fronteira de autenticação:

```text
Navegador
  -> sessão GitHub no Next.js
  -> ação executada no servidor Next.js
  -> API FastAPI autenticada entre servidores
  -> regras de negócio Python
  -> Google Sheets
```

O código da `main` é a fonte principal de verdade. `AGENTS.md` complementa as regras do produto. Registros históricos servem apenas para explicar decisões anteriores.

## 2. Objetivos

1. Dar à interface Next.js todas as operações de escrita que existem no Streamlit.
2. Reutilizar as regras de negócio Python atuais, especialmente as regras de sessões, revisões, erros, ciclo e XP.
3. Impedir acesso de qualquer conta GitHub diferente de `DaviFreitas-dev`.
4. Não expor tokens, credenciais do Google ou chaves privadas ao navegador.
5. Tornar tentativas repetidas seguras, sem registros ou XP duplicados.
6. Preservar dados antigos e linhas incompletas do Google Sheets.
7. Manter o Streamlit como escritor oficial até a validação completa da nova versão.
8. Permitir retorno rápido ao Streamlit sem migração reversa de dados.

## 3. Fora do escopo

Esta migração não adicionará:

- múltiplos usuários ou colaboração;
- notificações;
- sincronização com calendário;
- um editor avançado para o diário;
- um novo banco de dados;
- novas mecânicas de gamificação;
- refatorações sem relação direta com autenticação, escrita ou corte.

Esses itens podem ser avaliados depois da equivalência funcional e da estabilização da nova interface.

## 4. Decisões principais

### 4.1 Hospedagem e identidade

- O Next.js será hospedado na Vercel.
- O FastAPI será hospedado no Render.
- O login será feito com GitHub por meio do Auth.js.
- Somente a identidade GitHub `DaviFreitas-dev` poderá criar uma sessão válida. A autorização usará o ID numérico imutável da conta; o login será uma conferência secundária e o nome exibido.
- A proteção do produto será feita dentro do aplicativo; não dependerá apenas da proteção de preview da hospedagem.

### 4.2 Regras de negócio

As escritas não serão reimplementadas em TypeScript. O FastAPI chamará serviços Python que reutilizam as regras atuais de `modules/`. Isso mantém em um só lugar as validações, a atualização do ciclo, o agendamento 1-7-30, o caderno de erros e a concessão idempotente de XP.

O acesso ao Google Sheets será extraído para uma camada independente de Streamlit. A aplicação antiga e a API usarão o mesmo contrato de armazenamento, mas cada ambiente fornecerá suas próprias credenciais e cache. A interface Streamlit e a API não devem manter duas implementações diferentes da mesma regra de domínio.

### 4.3 Estratégia de substituição

O Streamlit continuará sendo o único escritor usado no dia a dia até que todas as operações da nova interface estejam prontas e testadas. Componentes e endpoints de escrita poderão ser publicados antes disso, mas permanecerão bloqueados por configuração.

O corte ocorrerá somente na quarta entrega descrita na seção 11.

## 5. Fronteiras de segurança

### 5.1 Navegador

O navegador receberá apenas a sessão segura da aplicação e dados necessários à tela. Ele nunca receberá:

- `NEXO_API_TOKEN`;
- JSON ou chave privada da Service Account;
- segredos do Auth.js;
- permissão direta para acessar o Google Sheets.

Formulários chamarão ações no servidor Next.js. A validação no cliente servirá para orientar o usuário, mas o servidor continuará sendo a autoridade.

### 5.2 Servidor Next.js

Antes de ler ou alterar dados protegidos, o servidor Next.js deverá:

1. validar a sessão Auth.js;
2. conferir o ID numérico autorizado e o login retornados pelo GitHub;
3. rejeitar qualquer conta diferente da autorizada;
4. validar e normalizar o formulário;
5. chamar o FastAPI com o segredo de comunicação entre servidores.

As páginas protegidas redirecionarão visitantes sem sessão para o login. Uma conta autenticada, mas não autorizada, verá uma recusa direta e não terá acesso parcial ao aplicativo.

### 5.3 FastAPI

O FastAPI continuará exigindo autenticação em todas as rotas de dados. As rotas de escrita também exigirão que `NEXO_API_WRITES_ENABLED` esteja explicitamente ativado. O valor ausente ou inválido significa **escritas bloqueadas**.

O servidor Next.js terá o gate privado separado `NEXO_WEB_WRITES_ENABLED`.
Ausente, inválido ou diferente de `true`, ele ocultará o formulário de criação
de tarefa. Esse controle de apresentação não substitui a revalidação da sessão,
o token servidor-a-servidor nem o gate do FastAPI.

A API será chamada apenas pelo servidor Next.js. Não será aberto um fluxo de escrita direto do navegador e não será necessário liberar CORS para o cliente.

O Streamlit terá um portão central separado, `NEXO_STREAMLIT_WRITES_ENABLED`. Nas três primeiras entregas, sua ausência manterá o comportamento legado para não interromper a aplicação atual. Na entrega de corte, o padrão passará a ser bloqueado e uma ativação explícita será reservada ao procedimento de retorno. Os controles da interface antiga também indicarão o modo somente leitura.

### 5.4 Segredos

Credenciais reais existirão somente nos gerenciadores de segredo da Vercel, Render e Streamlit Community Cloud. Arquivos de exemplo conterão apenas nomes e valores vazios. Logs, mensagens de erro e respostas HTTP não poderão incluir tokens, chaves ou o corpo completo de registros pessoais.

Os nomes previstos são:

- Vercel: `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, `AUTH_SECRET`, `NEXO_ALLOWED_GITHUB_ID`, `NEXO_API_URL` e `NEXO_API_TOKEN`;
- Vercel, para a mutação protegida: `NEXO_WEB_WRITES_ENABLED`, fechado por padrão;
- Render: `NEXO_API_TOKEN`, `GSHEETS_SERVICE_ACCOUNT_JSON`, `NEXO_API_WRITES_ENABLED` e `NEXO_TIMEZONE`;
- Streamlit Community Cloud: a seção atual `gsheets` e `NEXO_STREAMLIT_WRITES_ENABLED`.

Nenhuma dessas variáveis poderá usar o prefixo público `NEXT_PUBLIC_`.

## 6. Armazenamento e consistência

### 6.1 Camada compartilhada

A camada de armazenamento terá responsabilidade limitada a:

- abrir a planilha usando credenciais fornecidas pelo ambiente;
- ler abas em lote;
- criar abas ausentes sem apagar conteúdo;
- adicionar, atualizar e excluir linhas de forma pontual;
- executar as gravações em lote já usadas pelas operações compostas;
- invalidar o cache das abas alteradas.

Streamlit continuará responsável apenas por sua integração de secrets, cache e apresentação. FastAPI terá integração equivalente baseada em variáveis privadas do ambiente, sem depender de um contexto Streamlit.

### 6.2 Compatibilidade com dados legados

Todas as leituras continuarão tolerando campos ausentes. Identificadores sintéticos usados apenas para apresentação não poderão ser enviados como IDs persistentes de escrita.

Antes do corte, uma rotina não destrutiva atribuirá UUIDs somente às linhas mutáveis que ainda não possuem `id`. Ela preencherá apenas as células de ID vazias, sem reordenar, limpar ou regravar a aba inteira. A rotina será testada com dados legados e executada somente em quiescência, depois de parar todas as escritas Streamlit e fazer o backup. O dry-run definitivo persistirá um plano com os UUIDs exatos; o apply consumirá esse mesmo plano revisado e revalidará cabeçalhos e células vazias antes da gravação em lote.

Mudanças de cabeçalho deverão acrescentar colunas, nunca limpar uma aba. Nenhum ajuste de schema poderá apagar o histórico.

### 6.3 Concorrência

A primeira versão de escrita funcionará com uma instância e um processo do FastAPI. Todas as mutações passarão pelo bloqueio reentrante compartilhado que protege concessões de XP e conclusão de sessões. O Streamlit estará com escritas desativadas quando a API assumir essa função.

Essa restrição evita concorrência entre dois escritores sem introduzir um sistema distribuído desnecessário. Se o serviço precisar escalar horizontalmente no futuro, será necessário adotar um bloqueio distribuído ou substituir o armazenamento antes de aumentar o número de escritores.

## 7. Contrato das mutações

Cada mutação terá:

- um modelo Pydantic específico;
- validação de campos obrigatórios, datas, números e relações entre valores;
- um identificador estável da operação ou do registro;
- resposta tipada com o estado confirmado;
- um código de erro estável para a interface;
- invalidação do cache somente após a confirmação da escrita.

A API preferirá comandos de estado explícito. Por exemplo, usará `done=true` em vez de “alternar”. Repetir a mesma solicitação deverá manter o mesmo resultado.

### 7.1 Idempotência

- Cada formulário de criação receberá um UUID antes do primeiro envio e conservará esse valor enquanto houver tentativas. Repetir o envio com o mesmo UUID e o mesmo conteúdo retornará o registro existente; reutilizar o UUID com outro conteúdo retornará conflito.
- Atualizações definirão o novo estado, em vez de inverter o valor atual.
- Exclusões repetidas retornarão sucesso quando o registro já estiver ausente.
- Sessões de estudo usarão `session_id` estável.
- XP continuará usando `event_key` em `XPEventos`.
- Operações compostas preservarão o bloqueio e a gravação em lote existentes.

IDs de registros e chaves de XP têm finalidades diferentes. Um UUID evita duplicar o registro; o `event_key` evita premiar duas vezes o mesmo evento.

### 7.2 Respostas e falhas

A interface só mostrará sucesso depois da confirmação do Google Sheets. Em caso de falha:

- o formulário conservará o que foi digitado;
- a mensagem explicará a ação que não foi salva, sem texto genérico ou artificial;
- o botão voltará a ficar disponível de maneira segura;
- um identificador da operação permitirá localizar o erro nos logs;
- a interface poderá tentar novamente usando o mesmo identificador.

Erros de validação não chegarão ao Google Sheets. Falhas parciais de operações compostas deverão ser detectadas e nunca poderão conceder XP sem registrar a ação correspondente.

As respostas distinguirão falta de sessão, conta sem permissão, registro inexistente, conflito de idempotência, dados inválidos, escrita desativada e indisponibilidade temporária. A interface traduzirá essas categorias em mensagens curtas, sem exibir detalhes internos.

## 8. Escopo funcional de escrita

### 8.1 Hoje e captura rápida

- concluir ou reabrir tarefas;
- cumprir itens da rotina e agenda fixa;
- concluir revisões;
- marcar hábitos;
- registrar atividade física;
- criar tarefas rápidas;
- registrar prioridades de amanhã;
- adicionar uma entrada simples ao diário.

### 8.2 Planejar

- criar e arquivar itens da agenda semanal;
- registrar e desfazer check-ins pelo estado desejado;
- criar, concluir e excluir avaliações;
- concluir revisões 1-7-30;
- criar e resolver itens do caderno de erros;
- definir a meta semanal de questões;
- criar e concluir prioridades de amanhã;
- criar entradas do diário.

### 8.3 Rotina e vida pessoal

- criar, concluir, reabrir e excluir itens da rotina;
- criar, concluir, reabrir e excluir tarefas;
- criar, reativar e arquivar hábitos;
- marcar ou desmarcar o hábito do dia;
- cadastrar, atualizar, concluir, reabrir e excluir livros;
- registrar atividade física.

Arquivar um hábito preservará todo o histórico anterior.

### 8.4 Estudos

- salvar disciplinas, horas e ambiente;
- reiniciar o ciclo;
- sortear uma missão localmente a partir dos dados lidos;
- iniciar uma missão com `session_id` estável;
- concluir a missão informando disciplina principal, assunto, horas, questões, acertos, erros e anotação.

A conclusão usará obrigatoriamente `complete_study_session()`. A regra `acertos + erros == questões feitas` será validada antes da escrita. A operação atualizará pelo mesmo caminho ciclo, histórico, sessão, questões, revisões, caderno de erros e XP. Não existirá conclusão silenciosa.

### 8.5 Configurações

- salvar o edital e reiniciar o ciclo conforme a regra atual;
- reiniciar somente o ciclo;
- zerar o progresso após digitar exatamente `ZERAR PROGRESSO` e receber uma nova confirmação do servidor.

Zerar o progresso será a única operação destrutiva ampla desta etapa. Ela ficará visualmente separada das configurações comuns, não aceitará acionamento acidental e não será exercitada contra os dados reais durante testes automatizados.

### 8.6 Áreas de consulta

Progresso e Conquistas continuarão principalmente como análises de leitura. Conquistas desbloqueadas serão preservadas. Qualquer persistência necessária para atualizar conquistas será executada de forma controlada pelo backend, nunca por um clique decorativo no cliente.

## 9. Experiência visual e textual

A nova interface manterá o NEXO como produto de produtividade em primeiro plano e gamificação em segundo plano.

- tema escuro, profissional e responsivo;
- hierarquia clara, principalmente na tela Hoje;
- textos curtos e naturais em português;
- ausência de emojis decorativos, preservando apenas o indicador de sequência já aprovado;
- estados distintos de carregamento, vazio, sucesso e erro;
- botões bloqueados enquanto uma operação está em andamento;
- foco visível, contraste adequado e navegação por teclado;
- animações discretas entre 150 e 220 ms;
- respeito a `prefers-reduced-motion`;
- nenhuma parede de cards com o mesmo peso visual.

O valor digitado não desaparecerá quando uma operação falhar. Confirmações otimistas só poderão ser usadas em estados facilmente reversíveis; a mensagem final de sucesso sempre dependerá da resposta do servidor.

## 10. Cache e atualização da interface

Uma mutação bem-sucedida deverá:

1. invalidar no backend somente as abas afetadas;
2. retornar o estado confirmado ou os identificadores alterados;
3. invalidar ou revalidar no Next.js as áreas que consomem esses dados;
4. atualizar a tela sem uma segunda escrita.

O cache curto de leitura será mantido. Durante o corte, será aguardado pelo menos o maior TTL configurado antes da primeira escrita no novo caminho.

## 11. Entregas independentes

A implementação não será tratada como uma mudança única. Cada entrega terá seu próprio plano executável e só começará depois da validação da entrega anterior. O primeiro plano cobrirá exclusivamente a fundação segura.

### Entrega 1 — Fundação segura

- Auth.js com GitHub e allowlist de uma conta;
- proteção das páginas e ações do servidor;
- comunicação privada Next.js -> FastAPI;
- camada de armazenamento Python utilizável fora do Streamlit;
- modelos, erros, bloqueio global e portão de escrita;
- rotina idempotente para preencher IDs persistentes ausentes, ainda sem execução na planilha real;
- primeira mutação de baixo risco usada como referência;
- testes de autenticação, autorização, idempotência e cache.

### Entrega 2 — Rotina pessoal

- tarefas;
- rotina;
- hábitos;
- leitura;
- atividade física;
- ações correspondentes na tela Hoje.

### Entrega 3 — Estudos e planejamento

- agenda semanal e check-ins;
- avaliações;
- revisões;
- caderno de erros;
- meta semanal;
- prioridades e diário;
- configuração e reinício do ciclo;
- conclusão completa de missão;
- zerar progresso com confirmação reforçada.

### Entrega 4 — Deploy e corte

- configurações definitivas de Vercel e Render;
- comparação da leitura com a planilha real;
- backup;
- bloqueio do escritor Streamlit;
- ativação do escritor FastAPI;
- testes controlados de produção;
- documentação de retorno.

Cada entrega terá branch, testes, revisão de diff e Pull Request próprios. O merge das três primeiras não autoriza a API a escrever em produção.

## 12. Estratégia de testes

Cada mutação será desenvolvida a partir de um teste que falha antes da implementação.

### 12.1 Python e FastAPI

- testes unitários das regras de domínio;
- testes com armazenamento falso para criar, repetir, atualizar e excluir;
- validações de dados vazios ou legados;
- autenticação obrigatória;
- portão de escrita bloqueado por padrão;
- repetição segura do mesmo UUID;
- invalidação das abas corretas;
- concorrência serializada;
- consistência de `complete_study_session()`;
- ausência de XP duplicado.

### 12.2 Next.js

- sessão ausente, conta recusada e conta autorizada;
- segredo disponível somente no servidor;
- validação e normalização dos formulários;
- manutenção do conteúdo depois de erro;
- prevenção de duplo envio;
- atualização dos painéis depois do sucesso;
- textos, estados vazios, foco e movimento reduzido.

### 12.3 Verificações de entrega

- suíte Python completa;
- lint, testes, typecheck e build do Next.js;
- busca por credenciais ou arquivos secretos;
- revisão do diff;
- smoke test de leitura em preview;
- teste visual em computador e celular.

Testes automatizados nunca zerarão o progresso nem apagarão dados da planilha real. Escritas reais, quando necessárias na validação final, usarão registros identificáveis, de baixo risco e removíveis pelos fluxos normais do produto.

## 13. Publicação, corte e retorno

### 13.1 Antes do corte

1. publicar Vercel e Render com `NEXO_WEB_WRITES_ENABLED=false` e `NEXO_API_WRITES_ENABLED=false`;
2. validar login, bloqueio de conta não autorizada e leituras, sem ativar mutações;
3. comparar todas as leituras relevantes com o Streamlit e o Google Sheets;
4. executar as suítes completas e escolher uma janela curta de manutenção;
5. entrar em manutenção e parar **todas** as escritas Streamlit antes do dry-run definitivo; confirmar que nenhum fluxo antigo consegue alterar dados;
6. aguardar requisições em andamento e pelo menos o maior TTL de cache configurado;
7. exportar ou copiar a planilha como backup verificável já em quiescência;
8. gerar e persistir o plano definitivo com `python scripts/backfill_missing_ids.py --plan-out reviewed-backfill-plan.json`;
9. ainda em quiescência, revisar estado de cada aba, linha, célula e UUID exato; qualquer mudança invalida o plano e exige um novo dry-run;
10. aplicar exatamente o arquivo revisado com `python scripts/backfill_missing_ids.py --apply-plan reviewed-backfill-plan.json --confirm BACKFILL_IDS`;
11. verificar cabeçalhos, células alteradas, UUIDs e contagens antes de sair da manutenção;
12. confirmar que os gates FastAPI e web permaneceram fechados durante todo o dry-run, revisão, apply e verificação.

### 13.2 Corte

1. obter uma decisão explícita de corte somente depois da verificação do backfill;
2. confirmar que o Streamlit continua sem escritas e que existe apenas uma instância/processo no Render;
3. ativar `NEXO_API_WRITES_ENABLED` e executar mutações pequenas com IDs únicos, mantendo `NEXO_WEB_WRITES_ENABLED=false`;
4. conferir as abas afetadas, totais e `XPEventos`;
5. ativar `NEXO_WEB_WRITES_ENABLED` somente após a confirmação do caminho FastAPI;
6. validar a experiência completa pelo navegador.

O sistema nunca deverá manter Streamlit e FastAPI habilitados como escritores ao mesmo tempo.

### 13.3 Retorno

Se houver falha relevante:

1. desativar primeiro as escritas da API;
2. aguardar requisições em andamento e o cache;
3. confirmar que não existem operações pendentes;
4. reativar as escritas do Streamlit;
5. verificar as abas tocadas pelos testes;
6. registrar o motivo do retorno antes de uma nova tentativa.

Não haverá migração para outro banco nem migração reversa, pois as duas interfaces usam a mesma planilha e os mesmos schemas. O preenchimento pontual de IDs é compatível com o Streamlit e será preservado no retorno.

## 14. Observabilidade

O FastAPI terá endpoint de saúde sem consulta à planilha e logs estruturados com:

- horário;
- rota e tipo de operação;
- identificador da requisição;
- identificador estável da mutação;
- resultado e duração;
- abas afetadas, sem conteúdo das linhas.

Para a criação de tarefas, os eventos distinguirão `create`, `replay`,
`conflict` e `failure`, registrarão status, rota, `Tarefas` e o UUID da tarefa
somente depois de validado. O identificador de requisição/operação será usado
para correlação sem registrar o payload.

Tokens, credenciais, anotações, diário e corpos completos de formulário não serão registrados.

## 15. Critérios para considerar a migração concluída

A substituição do Streamlit estará concluída somente quando:

- as 12 áreas carregarem dados reais na nova interface;
- todas as operações listadas na seção 8 estiverem disponíveis e testadas;
- somente a conta GitHub autorizada conseguir entrar;
- nenhum segredo chegar ao navegador ou aos logs;
- tentativas repetidas não criarem registros ou XP duplicados;
- a conclusão de missão preservar todas as atualizações compostas;
- dados antigos continuarem legíveis;
- caches forem invalidados depois de escritas;
- a experiência funcionar em celular e computador;
- o corte e o retorno tiverem procedimentos verificados;
- todas as suítes e builds passarem;
- uma comparação final com o Google Sheets confirmar os resultados.

Até esses critérios serem atendidos, o Streamlit continua sendo a referência operacional de escrita.
