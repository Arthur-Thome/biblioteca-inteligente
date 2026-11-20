# Catálogo bibliográfico

## Escopo desta etapa

A Open Library continua como fonte primária. A API de busca fornece registros de obra e pode expor campos de edições associados à obra; portanto, a interface identifica `work_id` separadamente de `edition_id` e não trata toda correspondência de obra como prova de uma edição específica. O usuário confirma qualquer candidato antes da inclusão.

A busca manual aceita título, autor ou ISBN. O endpoint Flask mantém `GET /api/search` e a resposta `{"books": [...]}`, acrescentando o parâmetro opcional `type` (`title`, `author` ou `isbn`). Consultas inválidas são rejeitadas; os resultados continuam limitados e usam o mecanismo heurístico existente para OCR.

## Metadados normalizados

Os candidatos podem apresentar título, subtítulo, lista de autores, descrição disponível, ISBN-10/13 informado pela fonte, idioma, editora, ano, páginas, assuntos, URL de capa, origem, identificador da obra e origem de cada campo complementar. Campos ausentes permanecem vazios. Resultados Open Library carregam `metadata_scope=work`, e a interface os identifica como dados associados à obra, que podem variar por edição. Quando um ISBN exato vincula uma edição Google Books, o escopo passa a `work_and_edition` e o ID da edição é conservado. Não se estima ISBN, edição ou dado editorial.

O Open Library fornece dados de obra e edições. A pesquisa de obra não garante que um ISBN agregado pertença à edição exibida; por esse motivo, o ISBN permanece identificado como dado de obra e não é copiado para a coluna canônica `livros.isbn`. O Google Books só complementa um registro quando há ISBN normalizado exatamente coincidente e seu ID de volume fica registrado. Não ocorre fusão baseada apenas em título ou autor, nem a capa do Google Books é copiada ao candidato Open Library.

## Identidade e duplicatas

- Resultados repetidos da mesma obra Open Library são identificados por chave `OL...W`.
- Uma edição Google Books é identificada pelo ID de volume e só complementa por ISBN exato.
- ISBNs e IDs externos são chaves de identidade mais fortes que título; títulos iguais podem representar traduções e edições distintas.
- Registros existentes são reutilizados pela origem e identificador estável, enquanto cada associação pessoal continua protegida pela conta autenticada.
- A interface continua exigindo confirmação explícita. A pontuação `n/100` é heurística de ordenação e não representa probabilidade.

## Segurança e indisponibilidade

URLs de capa provenientes do Open Library são limitadas ao host oficial e nunca são buscadas pelo backend. Dados externos são tratados como não confiáveis e renderizados por `textContent`. Timeouts e respostas inválidas produzem erro controlado sem remover o texto OCR já reconhecido. O servidor limita o ritmo de chamadas Open Library e mantém cache local limitado por quantidade.

## Limitações conhecidas

O catálogo Open Library não garante cobertura nem precisão editorial uniforme. A integração Google Books permanece opcional e não se ativa sem `GOOGLE_BOOKS_API_KEY`. A busca Google é usada somente como complemento e depende de ISBN coincidente; não há agregação de resultados Google como candidatos independentes nesta versão.
