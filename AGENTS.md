# AGENTS.md — NEXO

Este arquivo existe para dar contexto permanente a agentes de código, especialmente o Codex, antes de qualquer alteração neste repositório.

## 1. Visão do projeto

O NEXO é um aplicativo pessoal de estudos e rotina feito em Python + Streamlit.

Objetivo: juntar organização pessoal, acompanhamento dos estudos, estatísticas e gamificação leve em um único app.

A interface deve parecer um aplicativo real de produtividade, com visual profissional, escuro e moderno. A gamificação deve continuar presente, mas sem deixar a experiência infantil ou exagerada.

Nome oficial na interface: **NEXO**.

Não voltar a usar nomes como:
- UFPB Academy
- Personal Command Center
- Academy
- qualquer subtítulo desnecessário explicando o que o app é

## 2. Stack

- Python
- Streamlit
- pandas
- gspread
- google-auth
- Google Sheets como persistência
- Streamlit Community Cloud para deploy
- GitHub para versionamento

## 3. Estrutura principal

- `app.py`: configuração do Streamlit, inicialização do banco e roteamento manual das páginas.
- `views/`: telas da aplicação.
- `modules/`: regras de negócio, dados, estudos, tarefas, rotina, questões, gamificação etc.
- `assets/style.css`: estilo global.
- `.streamlit/config.toml`: tema do Streamlit.
- `.streamlit/secrets.toml`: segredo local/deploy; nunca deve ir para o GitHub.

## 4. Navegação atual

A aplicação possui estas áreas:

- Hoje
- Planejar
- Rotina
- Ciclo
- Missões
- Leitura
- Tarefas
- Hábitos
- Atividade
- Progresso
- Conquistas
- Configurações

A tela **Hoje** deve ser o centro da experiência. O usuário deve conseguir resolver a maior parte do dia sem precisar entrar em várias outras páginas.

## 5. Banco de dados

Os dados ficam em um Google Sheets chamado atualmente `Banco_UFPB`.

Esse nome é legado do backend. Não usar `UFPB` novamente na interface.

As abas atuais são definidas em `modules/config.py` e incluem:

- Usuario
- Config
- Ciclo
- Historico
- Questoes
- SessoesEstudo
- Erros
- Revisoes
- AgendaSemanal
- AgendaCheckins
- Avaliacoes
- Metas
- Planejamento
- Diario
- XPEventos
- Rotina
- Tarefas
- Leitura
- HabitosConfig
- Habitos
- Atividade
- Conquistas

### Regras críticas do banco

1. Nunca apagar dados antigos apenas para ajustar schema.
2. Preservar compatibilidade com abas/linhas legadas.
3. Dados vindos do Sheets podem estar incompletos. Preferir `row.get(...)` quando apropriado em leituras tolerantes.
4. Não assumir que todas as linhas antigas possuem `id`.
5. Não expor credenciais.
6. Nunca versionar `.streamlit/secrets.toml`.
7. Evitar chamadas desnecessárias à API do Google Sheets.
8. O projeto usa cache curto para leituras e deve invalidá-lo depois de escritas.
9. Para atualizações pequenas, preferir operações pontuais em vez de limpar e regravar abas inteiras quando possível.
10. Ao criar novas abas, fazê-lo automaticamente sem destruir conteúdo já existente.

## 6. Ciclo de estudos

O ciclo mantém disciplinas, horas e ambiente.

Ambientes válidos:
- Mesa
- Transporte
- Ambos

O usuário configura as disciplinas e o sistema sorteia missões com base nas horas restantes do ciclo.

Ao concluir uma missão, o ciclo é atualizado e o progresso é registrado.

## 7. Missões e sessões de estudo

O sorteio de estudo é tratado como uma missão.

Ao finalizar uma missão, o app deve registrar informações reais do estudo antes de liberar a conclusão:

- disciplina principal
- assunto
- horas estudadas
- questões feitas
- acertos
- erros
- anotação rápida

Validação importante:

`acertos + erros == questões feitas`

A missão não deve ser finalizada silenciosamente sem registrar o fechamento.

As sessões de estudo alimentam histórico, questões, caderno de erros e revisões automáticas.

## 8. Questões e desempenho

O app acompanha:

- total de questões feitas
- acertos
- erros
- taxa de acerto
- desempenho por matéria
- evolução semanal
- histórico acumulado

Existe um gráfico de pizza de acertos x erros no progresso geral.

Evitar duplicar registros quando a mesma sessão já tiver sido salva.

## 9. Caderno de erros

Os erros devem poder gerar registros contendo:

- disciplina
- assunto
- quantidade
- observação
- status

O objetivo é identificar assuntos fracos e ajudar a decidir o que revisar.

Registros podem ser marcados como resolvidos, mas o histórico deve ser preservado.

## 10. Revisões automáticas

Após sessões de estudo, o sistema agenda revisões espaçadas no modelo:

- 1 dia
- 7 dias
- 30 dias

As revisões devem aparecer no planejamento e/ou na tela Hoje e podem ser concluídas.

Evitar criar revisões duplicadas da mesma origem.

## 11. Agenda semanal e rotina

O NEXO possui dois conceitos relacionados:

### Agenda semanal
Compromissos recorrentes, como:
- escola
- estudo
- academia
- curso
- outras atividades fixas

Os itens correspondentes ao dia devem aparecer automaticamente.

### Rotina
Atividades específicas por data e horário.

A interface pode combinar os dois conceitos para mostrar uma agenda diária coerente.

## 12. Provas, trabalhos e prazos

O usuário pode cadastrar avaliações e entregas com data.

Provas importantes podem ser apresentadas como **BOSS**.

A interface deve destacar:

- quantos dias faltam
- disciplina
- tipo
- meta relacionada, quando existir
- status

Não transformar toda tarefa comum em BOSS; usar esse conceito para avaliações relevantes.

## 13. Metas

O app pode acompanhar metas, especialmente:

- meta semanal de questões
- metas ligadas a prazos ou preparação

O progresso deve ser calculado usando dados reais do período correspondente.

## 14. Tarefas

As tarefas possuem:

- texto
- categoria
- data
- status

Devem poder ser:

- criadas
- concluídas
- reabertas
- excluídas

Evitar perder tarefas antigas durante mudanças de schema.

## 15. Hábitos

O sistema permite:

- criar hábitos
- marcar hábitos do dia
- arquivar hábitos
- acompanhar sequência

Ao arquivar um hábito, preservar o histórico anterior.

XP de hábito não pode ser ganho várias vezes pela mesma conclusão.

## 16. Atividade física

O usuário pode registrar treino/atividade física.

Esta área já teve dados legados incompletos. Leituras devem ser defensivas e não podem derrubar o app inteiro por `KeyError` em linhas antigas.

## 17. Leitura

O módulo de leitura acompanha:

- título
- autor
- página atual
- total de páginas
- meta diária
- status

O usuário pode concluir, reabrir e excluir livros.

## 18. Pomodoro

O Pomodoro não deve bloquear o processo do Streamlit com `time.sleep()` por vários minutos.

O cronômetro atual roda no navegador.

Qualquer refatoração deve preservar comportamento não bloqueante.

## 19. Diário e planejamento de amanhã

O app possui registro rápido de diário e prioridades do dia seguinte.

O diário é simples e não deve virar um editor complexo sem necessidade.

O planejamento de amanhã deve destacar poucas prioridades importantes, idealmente as três principais.

## 20. Gamificação

O app possui:

- XP
- níveis
- missões
- conquistas
- sequências
- BOSS

A gamificação deve recompensar ações reais, não cliques vazios.

XP pode vir de ações como:

- estudar
- resolver questões
- desempenho
- concluir tarefas
- concluir hábitos
- registrar atividade física
- concluir revisões
- cumprir rotina
- atingir metas
- cumprir prazos

### Regra crítica de XP

O mesmo evento não pode gerar XP repetidamente.

Usar `event_key`/identificador único em `XPEventos` para impedir farming de XP.

Antes de adicionar uma nova fonte de XP, garantir que existe uma forma confiável de deduplicação.

## 21. Conquistas

As conquistas podem usar marcos como:

- horas estudadas
- XP total
- 100 / 500 / 1.000 questões
- percentual de acerto
- sequência de dias
- revisões concluídas
- provas/BOSS concluídos

Conquistas já desbloqueadas devem continuar desbloqueadas.

## 22. Página Progresso

A página de progresso deve concentrar análises úteis, não apenas números decorativos.

Pode mostrar:

- horas estudadas
- média diária
- melhor dia
- sequência
- total de questões
- acertos
- erros
- aproveitamento
- gráfico Acertos x Erros
- desempenho por matéria
- evolução semanal do percentual de acertos
- resumo semanal
- assuntos que mais precisam de revisão

Priorizar informações que ajudem o usuário a decidir o que fazer depois.

## 23. Página Hoje

A tela Hoje é a mais importante do NEXO.

Ela deve priorizar, quando relevante:

- progresso do dia
- próximas atividades da agenda
- tarefas
- revisões pendentes
- próximo prazo/prova/BOSS
- meta semanal de questões
- sequência geral
- leitura atual
- hábitos
- atividade física
- prioridades
- captura rápida

Evitar transformar a tela em uma parede de cards. Manter hierarquia visual clara.

## 24. Visual e UX

Direção visual:

- tema escuro
- profissional
- moderno
- organizado
- responsivo
- gamificação leve

Manter:

- XP
- níveis
- missões
- conquistas
- BOSS
- barras de progresso

Evitar:

- aparência infantil
- excesso de emojis
- excesso de gradientes
- excesso de brilho/neon
- textos longos explicando o que o app é
- muitos cards com o mesmo peso visual
- telas carregadas

O app deve parecer produtividade primeiro e jogo em segundo plano.

## 25. Segurança e segredos

Nunca:

- imprimir secrets
- copiar private keys para arquivos versionados
- criar exemplos contendo credenciais reais
- colocar `.streamlit/secrets.toml` no repositório
- registrar tokens em logs

Se precisar documentar secrets, usar apenas nomes fictícios/estrutura de exemplo.

## 26. Antes de alterar código

Sempre:

1. Ler os arquivos relacionados.
2. Entender os dados usados pela mudança.
3. Conferir o schema em `modules/config.py`.
4. Verificar impacto em dados antigos do Google Sheets.
5. Identificar possíveis chamadas extras à API.
6. Confirmar se a alteração pode gerar XP duplicado.
7. Confirmar se alguma tela depende da estrutura antiga.

## 27. Depois de alterar código

Sempre:

1. Verificar sintaxe dos arquivos Python alterados.
2. Verificar imports internos.
3. Procurar possíveis `KeyError` em dados vindos do Sheets.
4. Procurar `int(...)`/`float(...)` em valores que podem vir vazios/legados.
5. Verificar duplicação de chamadas à API.
6. Confirmar invalidação do cache após escritas.
7. Confirmar que nenhuma credencial foi adicionada.
8. Revisar o diff completo.
9. Verificar se dados antigos continuam legíveis.
10. Só considerar a mudança concluída quando não houver erro evidente.

## 28. Fluxo Git preferido

Para mudanças relevantes:

1. Criar branch a partir de `main`.
2. Implementar a mudança.
3. Revisar o diff.
4. Corrigir problemas encontrados.
5. Fazer segunda revisão.
6. Abrir Pull Request para `main`.
7. Mesclar apenas quando a mudança estiver coerente.

Evitar mudanças grandes diretamente na `main`.

## 29. Filosofia de produto

O NEXO não deve ser apenas um dashboard que registra coisas.

Ele deve ajudar a responder:

- O que eu devo estudar agora?
- O que preciso revisar?
- Em quais assuntos estou errando mais?
- Qual prova ou prazo está chegando?
- Minha meta semanal está atrasada?
- O que é prioridade hoje?
- Estou melhorando de verdade?

Quando houver escolha entre adicionar mais elementos decorativos ou melhorar uma dessas respostas, priorizar utilidade.