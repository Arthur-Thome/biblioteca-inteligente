# Google Books

Google Books é uma integração complementar opcional. O adaptador usa somente a busca pública `volumes.list`, limita a oito itens e tempo de conexão/leitura, valida `items`, `volumeInfo` e cada campo antes de normalizar os metadados. A chave, quando existente, permanece no servidor e é lida de `GOOGLE_BOOKS_API_KEY` no ambiente ou no `.env` local, que é ignorado pelo Git.

Sem chave configurada, o provedor fica desativado sem falha e a busca Open Library continua normalmente. Não há chave neste arquivo de documentação, não se cria projeto Google, não se habilita faturamento e não se envia imagem para Google Books. A integração não faz busca Google para criar candidatos paralelos; tenta somente preencher campos ausentes quando encontra ISBN-10 ou ISBN-13 exatamente correspondente. IDs de volume são registrados como identidade de edição complementar, não substituem o ID da obra Open Library.

Falha HTTP, timeout ou JSON incompleto é registrada sem credencial e não apaga o resultado Open Library. O adaptador não acessa coleções privadas nem recursos que exigem autenticação de conta.

Referências oficiais: [guia de uso e busca](https://developers.google.com/books/docs/v1/using), [volumes.list](https://developers.google.com/books/docs/v1/reference/volumes/list), [recurso Volume](https://developers.google.com/books/docs/v1/reference/volumes).
