# NEXO — Entrega 2: rotina pessoal

## 1. Contexto

A Entrega 1 criou a fronteira segura de escrita entre a interface Next.js, a API FastAPI e o Google Sheets. Ela também entregou a criação idempotente de tarefas como referência, mantendo os portões de escrita desligados.

A Entrega 2 amplia essa fundação para tarefas, rotina, hábitos, leitura, atividade física e as ações equivalentes da tela Hoje. O Streamlit continua sendo o escritor operacional até o corte da Entrega 4.

Este documento detalha a Entrega 2 sem substituir a especificação geral em `2026-08-23-nexo-write-migration-design.md`.

## 2. Objetivos

- permitir que a interface Next.js execute todo o ciclo de vida da rotina pessoal;
- manter as regras de negócio e XP nos módulos Python;
- tornar criações e alterações seguras para repetição;
- preservar a leitura de linhas legadas incompletas;
- impedir escritas implícitas durante requisições de leitura;
- reutilizar as mesmas ações nas páginas específicas e na tela Hoje;
- oferecer estados de formulário claros, naturais e acessíveis;
- manter os portões de escrita desligados após o merge.

## 3. Fora do escopo

- check-ins de `AgendaSemanal` e alterações em `AgendaCheckins`;
- avaliações, revisões, caderno de erros, metas, prioridades e diário;
- ciclo de estudos, missões e sessões;
- execução do backfill na planilha real;
- configuração de produção, ativação dos portões ou corte do Streamlit;
- reformulação visual de áreas que não participam dos fluxos desta entrega.

## 4. Decisões de arquitetura

### 4.1 Rotas por domínio

A API terá contratos separados para tarefas, compromissos avulsos, hábitos, livros e atividade física. Não será criado um endpoint genérico de comandos. Cada contrato terá modelos próprios, validação explícita, resposta tipada e mensagens de erro adequadas ao domínio.

Todas as mutações seguirão a ordem:

1. autenticar o token privado da API;
2. verificar `NEXO_API_WRITES_ENABLED`;
3. validar e normalizar os dados;
4. adquirir o bloqueio global de mutação;
5. executar a regra do módulo Python;
6. invalidar somente os caches afetados;
7. retornar o estado confirmado e o `operationId`;
8. registrar o resultado sem conteúdo pessoal ou segredos.

### 4.2 Servidor Next.js

O navegador não conhecerá o token da API. Toda alteração passará por uma Server Action que:

1. exige a sessão GitHub autorizada;
2. verifica `NEXO_WEB_WRITES_ENABLED`;
3. valida o `FormData`;
4. envia a solicitação pelo cliente privado existente;
5. confere se a resposta confirma a operação pedida;
6. revalida as páginas afetadas somente após sucesso.

As páginas específicas e a tela Hoje compartilharão ações e componentes de interação. Não haverá uma segunda implementação das regras para a tela Hoje.

### 4.3 Módulos Python

Os módulos em `modules/` continuarão sendo a fonte das regras de negócio para Streamlit e FastAPI. Eles serão fortalecidos com:

- normalização de entrada;
- retornos com o registro confirmado;
- conflitos explícitos para IDs reutilizados com outro conteúdo;
- alterações por estado desejado, e não por inversão cega;
- invalidação de cache após toda escrita;
- tolerância a linhas antigas nas leituras.

## 5. Escopo funcional

### 5.1 Tarefas

- manter a criação idempotente já entregue;
- concluir ou reabrir pelo estado desejado;
- excluir de forma segura para repetição;
- refletir a alteração em `/tarefas`, `/` e nas leituras agregadas relacionadas.

Uma conclusão concede XP pelo `event_key` atual `task:<id>`. Reabrir ou repetir a conclusão não concede XP novamente.

### 5.2 Rotina

- criar compromisso avulso com data, horário e atividade;
- concluir ou reabrir pelo estado desejado;
- excluir de forma segura para repetição.

A criação receberá um UUID gerado antes do primeiro envio. Uma conclusão concede XP por `routine:<id>` apenas uma vez.

Os itens fixos de `AgendaSemanal` continuam somente para leitura nesta entrega. Seus check-ins pertencem à Entrega 3.

### 5.3 Hábitos

- criar um hábito novo;
- reativar um hábito arquivado com o mesmo nome normalizado;
- arquivar sem remover a configuração ou o histórico;
- marcar ou desmarcar um hábito em uma data.

Carregar hábitos será uma operação estritamente de leitura. A função de leitura não criará mais linhas ausentes em `Habitos`. Ao marcar ou desmarcar, a mutação localizará o registro pela data e pelo hábito; se ele ainda não existir, criará dentro do bloqueio global uma linha com UUID determinístico derivado do ID da configuração e da data. Assim, tentativas repetidas convergem para o mesmo registro.

O XP continuará deduplicado por `habit:<log_id>`. Arquivar um hábito não altera registros anteriores.

### 5.4 Leitura

- cadastrar título, autor opcional, total de páginas e meta diária;
- atualizar a página atual;
- concluir o livro;
- reabrir o livro;
- excluir o livro.

Página atual, total e meta serão inteiros não negativos, com total e meta maiores que zero. A página atual não poderá ultrapassar o total. Alcançar a última página confirmará o estado `Concluído`; reabrir preservará a página atual.

### 5.5 Atividade física

- registrar tipo e data;
- reconhecer a repetição do mesmo tipo na mesma data sem criar outra linha;
- confirmar como concluído um registro legado compatível que ainda esteja pendente.

O XP será deduplicado pelo `event_key` atual `activity:<data>:<tipo-normalizado>`. Repetir a solicitação não criará novo registro nem novo XP.

### 5.6 Tela Hoje

A tela Hoje ganhará controles para as operações desta entrega que aparecem no painel:

- concluir e reabrir tarefas do dia;
- concluir e reabrir compromissos avulsos da rotina;
- marcar e desmarcar hábitos;
- atualizar a leitura em andamento;
- registrar atividade física;
- criar uma tarefa rápida.

Itens fixos da agenda serão exibidos sem controle de check-in até a Entrega 3. A interface deixará essa condição clara sem apresentar um botão inoperante.

## 6. Idempotência e consistência

Criações de tarefas, compromissos e livros usarão UUID gerado no servidor Next.js antes da primeira tentativa. Repetir o mesmo UUID e o mesmo conteúdo devolverá o registro existente; reutilizá-lo com conteúdo diferente produzirá `idempotency_conflict`.

Alterações usarão o estado desejado, como `completed: true`, `active: false`, `status: "Lendo"` ou `currentPage: 80`. Repetir o estado já confirmado será sucesso sem nova escrita desnecessária e sem novo XP.

Exclusões tratarão um registro já ausente como estado final confirmado. A resposta informará se houve remoção nesta tentativa, permitindo que uma repetição seja segura.

Atividade física e check-ins de hábito terão, além do ID, uma chave semântica de unicidade. Todas as buscas, gravações relacionadas e concessões de XP ocorrerão sob o mesmo bloqueio global.

Operações que gravam o registro principal e XP serão consideradas bem-sucedidas apenas após a regra completa terminar. Uma falha parcial será registrada como erro e nunca será apresentada pela interface como sucesso.

## 7. Compatibilidade com dados legados

As leituras continuarão aceitando campos ausentes, números vazios e linhas sem ID. Conversões numéricas usarão valores seguros e não derrubarão a área inteira.

Registros sem ID serão exibidos, mas controles que exigem identidade persistente ficarão indisponíveis até o backfill revisado. A interface mostrará uma explicação curta, sem expor detalhes da planilha.

Nenhuma mutação procurará um registro apenas pela posição da linha. As exceções são as chaves semânticas deliberadas de hábitos e atividade, sempre acompanhadas de validação do conteúdo encontrado.

## 8. Cache e revalidação

Depois de uma escrita, a camada Python invalidará as abas diretamente afetadas e os agregados que dependem delas. A interface revalidará somente os caminhos consumidores:

- tarefas: `/tarefas` e `/`;
- rotina: `/rotina` e `/`;
- hábitos: `/habitos` e `/`;
- leitura: `/leitura` e `/`;
- atividade: `/atividade` e `/`.

Uma revalidação nunca executará uma segunda escrita. A leitura de hábitos será corrigida para não produzir efeitos colaterais.

## 9. Experiência de uso

Os formulários manterão os valores digitados quando houver falha. Botões ficarão bloqueados durante o envio e mudanças de estado só serão confirmadas após a resposta da API. Exclusões terão confirmação explícita no contexto do item.

Mensagens serão curtas e naturais em português. Erros internos, nomes de variáveis, tokens, planilhas e rastros não aparecerão para o usuário. O `operationId` ficará disponível apenas como referência discreta quando ajudar no diagnóstico.

Os controles terão foco visível, rótulos acessíveis, região `aria-live` para resultado e suporte a teclado. Animações usarão a faixa existente de 150 a 220 ms e respeitarão `prefers-reduced-motion`.

Enquanto `NEXO_WEB_WRITES_ENABLED` estiver desligado, os controles de gravação ficarão indisponíveis com uma explicação única e clara. A interface não fingirá que salvou algo.

## 10. Erros

Os contratos distinguirão:

- `invalid_token` e `authentication_unavailable`;
- `writes_disabled`;
- `invalid_request`;
- `record_not_found` para alterações que precisam de um registro existente;
- `idempotency_conflict`;
- `write_failed` para indisponibilidade temporária;
- `ambiguous_api_response` quando o Next.js não puder confirmar a resposta.

A API não devolverá exceções ou detalhes do Google Sheets. A interface mapeará as categorias para mensagens específicas e preservará os dados do formulário para uma nova tentativa.

## 11. Testes

A implementação seguirá testes antes do código de produção.

### 11.1 Python e FastAPI

- criação, repetição, conflito, alteração por estado desejado e exclusão repetida;
- token ausente ou incorreto e autenticação indisponível;
- portão desligado antes de qualquer acesso ao Sheets;
- validação de texto, datas, horários, números e estados;
- linhas legadas incompletas e registros sem ID;
- hábitos sem escrita durante leitura;
- deduplicação de atividade e XP;
- invalidação apenas dos caches afetados;
- falhas de armazenamento convertidas em respostas seguras;
- logs estruturados sem conteúdo pessoal ou segredos.

Os testes usarão planilhas falsas. Nenhum teste automatizado acessará a planilha real.

### 11.2 Next.js

- sessão obrigatória e allowlist preservada;
- portão web desligado antes da chamada à API;
- validação dos formulários e preservação dos valores após erro;
- UUID estável em repetição e renovado somente após sucesso confirmado;
- mapeamento das categorias de erro;
- conferência da resposta antes da revalidação;
- revalidação dos caminhos corretos;
- estados pendente, sucesso, erro, confirmação e prevenção de envio duplo;
- reutilização dos controles na tela Hoje.

Serão adicionados testes de componentes com ambiente DOM para cobrir interações reais de formulário, incluindo bloqueio do botão, reset após sucesso e repetição rápida do envio.

### 11.3 Verificação final

- suíte Python completa;
- compilação e imports dos módulos alterados;
- suíte web completa;
- lint, tipos e build do Next.js;
- testes dos artefatos de Server Actions;
- revisão de segurança, compatibilidade legada, XP e cache;
- revisão integral do diff e segunda revisão independente.

## 12. Entrega e segurança operacional

O trabalho acontecerá na branch `agent/nexo-personal-routine`, em worktree isolada e com Pull Request próprio.

O merge não autoriza escrita na API, execução de backfill, deploy de novos serviços ou corte do Streamlit. Ao final desta entrega:

- `NEXO_API_WRITES_ENABLED` permanece `false`;
- `NEXO_WEB_WRITES_ENABLED` permanece `false`;
- o Streamlit continua como escritor operacional;
- a ativação real continua reservada à Entrega 4.
