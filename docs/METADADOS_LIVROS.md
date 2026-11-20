# Metadados bibliográficos

## Registro comum da interface

O catálogo normaliza campos para título, subtítulo, autores, descrição, ISBN-10, ISBN-13, idioma, editora, ano, páginas, gêneros/assuntos, URL de capa, provedor, ID de obra e ID de edição. Campos desconhecidos permanecem `null`, vazios ou ausentes. O sistema não preenche dados por inferência. O campo `metadata_scope` distingue dados de obra (`work`) de obra ligada a edição identificada por ISBN (`work_and_edition`), e a interface apresenta esse escopo.

## Persistência

Os campos já existentes no modelo continuam em colunas específicas. A migração `9a7d31f2c4e8` acrescenta `livros.metadados` como JSONB com objeto vazio padrão, para subtítulo, ISBNs separados, idioma, editora, páginas, IDs complementares e `metadata_sources`. A migração é aditiva e não reescreve linhas existentes. A coluna `isbn` já existente conserva o índice de unicidade; ISBN extraído de uma busca em nível de obra não é copiado automaticamente para ela.

Cada origem por campo é restrita a `openlibrary` ou `google_books`. Google Books só complementa campo ausente após correspondência exata de ISBN normalizado; título semelhante, autor comum ou capa coincidente não bastam para mesclar edições. O candidato principal permanece identificado pela chave Open Library. ISBN agregado à obra não é copiado para a coluna única de ISBN, e as capas não são mescladas entre provedores.

## Capa e interface

Capas Open Library usam URL oficial previamente validada. Candidatos sem capa exibem o marcador local existente. O navegador trata texto bibliográfico com `textContent`; o backend não busca URLs externas fornecidas pelo cliente, o que impede uso dessa funcionalidade para SSRF.

## Limites

Os metadados dependem da cobertura e da qualidade dos catálogos. O Open Library pode associar vários ISBNs a uma obra sem identificar qual edição foi fotografada. Dados de provedores não são evidência de que a pessoa possui determinada edição. A confirmação do candidato permanece obrigatória.
