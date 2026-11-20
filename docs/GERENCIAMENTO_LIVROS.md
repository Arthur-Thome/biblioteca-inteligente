# Gerenciamento de livros

## Contratos HTTP

| Método e rota | Finalidade | Acesso e validação |
|---|---|---|
| `GET /api/library` | Pesquisa, filtros, ordenação, totais e paginação da coleção | Exige sessão; tamanho e página são limitados; ordenações usam lista permitida |
| `GET /api/library/<uuid:item_id>` | Consulta os dados bibliográficos e pessoais de uma associação | Exige sessão; associação de outra conta retorna 404 |
| `PATCH /api/library/<uuid:item_id>` | Atualiza favorito e/ou observação pessoal | Exige sessão e CSRF; só aceita campos previstos e nota de até 2.000 caracteres |
| `DELETE /api/library/<uuid:item_id>` | Remove o livro da coleção da conta | Exige sessão e CSRF; não apaga o registro bibliográfico compartilhado |

## Pesquisa e filtros

`GET /api/library` aceita `q` para título, autor e ISBN; `author` e `subject` para filtros adicionais; `favorites=true` para favoritos; `sort` para `title_asc`, `title_desc`, `author_asc`, `added_newest` ou `added_oldest`; além de `page` e `page_size`. A rota limita o tamanho máximo a 48 e usa 12 como tamanho inicial. Os critérios são compostos no repositório SQLAlchemy com bind parameters e escopo obrigatório de `usuario_id`; valores enviados não viram identificadores SQL.

A resposta contém uma lista `books`, o objeto `pagination` com página, tamanho, total filtrado e páginas, `summary` com totais da coleção e favoritos, e `filters` com os critérios ativos. A ordenação secundária por título e identificador estabiliza resultados empatados.

## Atualização pessoal e exclusão

Favorito e observação são atributos da associação usuário/livro em PostgreSQL. A rota PATCH valida o tipo booleano, aceita observação textual ou nula e aplica limite de 2.000 caracteres tanto na aplicação quanto no banco. Os valores não alteram a linha bibliográfica compartilhada. Detalhes e alterações consultam associação pelo proprietário; IDs válidos de outra conta não revelam se o registro existe e recebem 404.

A interface atualiza o DOM usando nós de texto e `textContent`. O pedido de remoção requer confirmação visual e o backend mantém a regra de propriedade. A mutação exige CSRF, assim como as operações existentes.

## Verificação funcional

`scripts/verificar_ui_etapa8.py` executa o fluxo de ponta a ponta contra `biblioteca_inteligente_test`: OCR e catálogo reais quando disponíveis, inclusão autenticada, filtros combinados, favoritos, observações, recarga, ordenação, paginação, recomendações, isolamento, remoção e viewports de notebook e celular. Dados gerados pelo roteiro são limitados à conta de teste e removidos ao final.
