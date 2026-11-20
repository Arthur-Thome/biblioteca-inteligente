# Recomendações

## Algoritmo implementado

`backend/recomendacoes.py` mantém a Open Library como fonte externa e a seleção de assuntos como mecanismo principal. A rota `POST /api/recommend` obtém a biblioteca e preferências diretamente da sessão PostgreSQL; dados enviados livremente no corpo não escolhem o proprietário. Assuntos específicos de livros, assuntos de livros favoritos e até quatro interesses explícitos produzem consultas; preferências com nível maior são consultadas primeiro. Catálogo e recomendações continuam heurísticos.

Os candidatos são excluídos quando o identificador ou título normalizado já pertence à biblioteca. Resultados repetidos por identificador são agregados, ranqueados por correspondência de assuntos/interesses e desempate textual. Cada indicação inclui motivo em linguagem simples, como assunto compartilhado ou interesse registrado. O campo `score` é apenas ordenação heurística e não é probabilidade ou porcentagem de acerto. A pessoa usuária ainda confirma candidatos ao adicioná-los.

## Casos de poucos dados

Uma biblioteca vazia recebe orientação para adicionar um livro. Quando há livros sem assuntos utilizáveis, a interface explica a limitação do catálogo. Preferências podem ampliar as consultas mesmo quando os metadados dos livros são escassos. A solução não inventa preferência na ausência de histórico ou interesses declarados.

## Preferências

`GET /api/preferences`, `POST /api/preferences` e `DELETE /api/preferences/<UUID>` permitem listar, registrar e remover assunto ou gênero da própria conta. O POST exige CSRF, valida categoria, texto e nível de 1 a 5; duplicatas normalizadas recebem conflito. Preferências são armazenadas na tabela existente e nunca são compartilhadas entre contas.

## Integração

`templates/index.html` contém `#recommend-btn`, `#recommend-results`, `#recommend-status` e o formulário `#preference-form`. `static/app.js` chama `POST /api/recommend`, além dos endpoints de preferência, e cria resultados com texto DOM seguro. `backend/routes.py` obtém livros e favoritos de `backend.repositories.biblioteca` e preferências de `backend.repositories.preferencias`. `backend.recomendacoes.recommend_books` consulta o cliente `backend.catalogo.search_books`, que acessa Open Library. Falhas externas mantêm respostas controladas HTTP 503.

## Limitações

A qualidade depende dos assuntos e metadados retornados pelo catálogo e de conectividade. Não há modelo treinado de recomendação, avaliação de preferência com usuários, nem calibração estatística do ranking. A página não descreve pontuação heurística como confiança.
