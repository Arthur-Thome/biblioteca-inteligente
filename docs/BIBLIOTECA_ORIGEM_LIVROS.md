# Origem nacional ou internacional da obra

## Campo pessoal

`biblioteca_usuario.origem_obra` classifica a origem da obra por associação individual entre conta e livro. O campo aceita `nacional`, `internacional` e `nao_informado`, com padrão `nao_informado`. A migração aditiva `d1a45f8c2e70` cria a coluna, uma restrição CHECK e um índice por usuário/origem sem reescrever metadados compartilhados.

Nacional identifica obra brasileira, qualquer que seja o idioma da edição. Internacional identifica obra estrangeira. A classificação não é inferida automaticamente do idioma, ISBN ou editora; a seleção é feita pela pessoa usuária.

## Interface e integração

`templates/index.html` contém o filtro `#origin-filter` e a seleção `#origin-obra` nos detalhes. `static/app.js` serializa o filtro em `GET /api/library?origin=...` e envia a classificação via `PATCH /api/library/<id>` com CSRF. `backend/routes.py` valida o valor e passa o UUID do proprietário obtido da sessão a `backend/repositories/biblioteca.py`, que filtra e atualiza somente a associação daquela conta.

O filtro é aplicado no PostgreSQL em conjunto com consulta, autor, assunto, favoritos, ordenação e paginação. O card exibe `Nacional`, `Internacional` ou `Origem não informada`. Os controles de favorito e remoção permanecem independentes da área clicável que abre os detalhes.

## Datas e rótulos bibliográficos

`backend/routes.py` serializa instantes com fuso em ISO 8601 UTC, sem mudar o valor armazenado. `static/formatters.js` apresenta o instante no fuso `America/Sao_Paulo`, com localidade `pt-BR` e formato `DD/MM/AAAA às HH:mm`. Valores ausentes ou inválidos são apresentados como `Não informado`. O acesso de leitura aos detalhes não altera `atualizado_em`.

O mesmo formatador apresenta rótulos conhecidos para `spa`, `por`, `eng`, `fre`, `fra`, `openlibrary` e `google_books`; o metadado original permanece no JSON e códigos desconhecidos não são reinterpretados.

## Verificações

Os testes Python verificam criação e atualização por proprietário, filtro combinado, CSRF e isolamento. `tests/test_formatters.js` verifica timestamps com offset, UTC, microssegundos, valores inválidos e códigos conhecidos. A homologação com navegador cobre o card, a abertura por teclado, datas e classificação.
