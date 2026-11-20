# Metas de leitura

## Regra de progresso

Cada meta pertence a `usuarios` e define uma quantidade positiva de livros e intervalo com início anterior ao fim. O usuário cria a meta voluntariamente; nenhuma meta é adicionada automaticamente. A tabela `metas_leitura` e suas restrições já existiam, então a Etapa 9 não criou migração.

O progresso é recalculado a partir de associações próprias cujo estado atual seja `concluido` e cuja data de conclusão caia no período inclusivo. A consulta conta IDs distintos de associação, portanto um livro não conta várias vezes na mesma meta. A quantidade restante é limitada a zero e o percentual visual é limitado a 100. O encerramento do intervalo é convertido em limite exclusivo à meia-noite UTC do dia seguinte, evitando perder conclusões ocorridas no último dia.

## Rotas e validação

- `GET /api/goals` lista somente metas da sessão e devolve quantidade concluída, restante e percentual.
- `POST /api/goals` cria meta, exige CSRF e aceita objetivo inteiro de 1 a 500 e datas ISO válidas.
- `PUT /api/goals/<UUID>` altera objetivo e período da meta própria.
- `DELETE /api/goals/<UUID>` exclui somente meta própria e exige CSRF.

O intervalo final deve ser posterior ao inicial e não pode exceder dez anos. Um período idêntico existente retorna conflito em vez de criar duplicata. IDs e proprietário são conferidos no repositório; uma meta de outra conta retorna 404. A aplicação usa `backend.repositories.metas` e a função `contar_livros_concluidos`; nenhum ID de conta vem do formulário.

## Interface

`templates/index.html` fornece `#goal-form`, objetivo e datas, lista `#goals-list` e status `#goals-status`. O CSS em `static/style.css` controla a grade responsiva e a barra de progresso. `static/app.js` executa POST/PUT/DELETE com CSRF, mostra ações de edição e exclusão e atualiza a lista. A exclusão pede confirmação. A conclusão de leitura atualiza os indicadores ao recarregar metas.

## Testes

Os testes PostgreSQL e HTTP verificam CRUD, datas, objetivo, conflito de período, cálculo baseado em leitura concluída, valor restante, CSRF e isolamento entre contas. A execução efetiva está descrita em `docs/TESTES.md`.
