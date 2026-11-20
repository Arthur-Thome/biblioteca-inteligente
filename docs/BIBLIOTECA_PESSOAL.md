# Biblioteca pessoal

## Escopo da Etapa 8

A biblioteca pessoal oferece uma consulta paginada à coleção da conta autenticada. A pesquisa interna por título, autor ou ISBN é independente da busca de novos livros no catálogo. Filtros de autor, assunto e favoritos podem ser combinados com a pesquisa e com a ordenação.

O navegador consulta `GET /api/library` com `q`, `author`, `subject`, `favorites`, `sort`, `page` e `page_size`. A rota valida os limites e as opções permitidas, obtém o identificador da conta da sessão e chama `listar_pagina_usuario`. A resposta inclui `books`, `pagination`, `summary` e `filters`. A consulta não busca dados externos e não carrega a coleção inteira.

## Dados pessoais e detalhes

As informações bibliográficas permanecem em `livros`. Favorito e observação pertencem à linha de `biblioteca_usuario`, que associa o livro à conta. A revisão Alembic `c4e8a19f07d2` acrescenta `favorito` com padrão falso, `observacoes_pessoais` opcional limitado a 2.000 caracteres, índice por usuário/favorito e restrição equivalente no PostgreSQL. `atualizado_em` registra mudanças na associação.

`GET /api/library/<uuid:item_id>` devolve os detalhes apenas quando a associação pertence à sessão ativa. `PATCH` aceita somente `favorite` booleano e/ou `notes` como texto ou nulo. A proteção CSRF global permanece obrigatória para a alteração. O repositório limita a atualização à associação do proprietário. Observações retornam como dados JSON e são atribuídas ao DOM como texto, sem interpretação de HTML.

## Remoção e privacidade

A remoção continua em `DELETE /api/library/<uuid:item_id>` e exige sessão e CSRF. A interface solicita confirmação e a rota restringe a exclusão ao proprietário. Dados bibliográficos compartilhados não são apagados ao remover uma associação.

Os totais da tela referem-se à coleção inteira da conta; a quantidade mostrada na página atual respeita filtros. A consulta, os filtros, os detalhes e as mutações são limitados ao usuário autenticado. O formato legado do `localStorage` permanece inalterado e não participa desta área.

## Interface

`templates/index.html` contém os controles identificados por `library-query`, `library-author`, `library-subject`, `favorites-only` e `library-sort`, além do diálogo `book-details-dialog`. `static/style.css` define filtros, cards, controles de favorito, diálogo e adaptação para telas estreitas. `static/app.js` gerencia eventos, consulta paginada, atualização de cards, detalhes e mutações com o token CSRF.

As capturas do fluxo autenticado estão em `docs/evidencias/etapa8-biblioteca-notebook.png` e `docs/evidencias/etapa8-biblioteca-celular.png`. A execução Playwright documentada em `docs/TESTES.md` verificou filtros, ordenação, paginação, detalhe, favorito, observação e persistência no banco de teste.

## Limites

O sistema não implementa importação do `localStorage`, progresso de leitura, metas, edição de metadados bibliográficos ou sincronização entre contas. A listagem usa os dados já persistidos e não depende da disponibilidade da Open Library.
