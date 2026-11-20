# Avaliação do catálogo bibliográfico

## Método

A suíte simulada verifica transformação de resultados, busca por autor/ISBN, ausência de configuração Google, complementação por ISBN exato e rejeição de tipo de consulta inválido. Esses casos não são contados como consultas reais.

As verificações reais usam consultas curtas a fontes oficiais, timeout limitado e intervalo de requisição Open Library. A métrica de recuperação considera `Recall@3`: presença do título esperado entre os três primeiros resultados. A primeira posição é registrada separadamente. A heurística de similaridade não é apresentada como probabilidade calibrada.

## Referência de implementação anterior

A implementação anterior consultava somente Open Library por `q`, usava título e autor reduzidos, sem ISBN, descrição, subtítulo, idioma, editora ou número de páginas na resposta da interface. Cache limitado por quantidade não expirava. Não havia escolha de busca por autor ou ISBN, nem proveniência dos campos.

## Resultado experimental real

Em 20/11/2026, `scripts/avaliar_catalogo.py` executou uma comparação pareada: cada uma das nove consultas foi enviada à implementação anterior (busca geral `q`) e à implementação atual (tipo de busca, metadados expandidos e fallback tolerante para títulos). A amostra não teve chave Google Books configurada. A similaridade para as métricas foi comparada após normalização Unicode; correspondência exige RapidFuzz `ratio >= 90`. O tempo inclui a consulta HTTP e não é somente tempo de CPU.

| Tipo | Consulta | Esperado | Top-1 anterior | Top-1 atual | Atual no top 3 |
|---|---|---|---|---|---:|
| Título | The Hobbit | The Hobbit | The Hobbit | The Hobbit | Sim |
| Título | Harry Potter and the Philosopher's Stone | Harry Potter and the Philosopher's Stone | Mesmo título | Mesmo título | Sim |
| Título | Dom Casmurro | Dom Casmurro | Dom Casmurro | Dom Casmurro | Sim |
| Título com acento | Dom Casmúrro | Dom Casmurro | Dom Casmurro | Dom Casmurro | Sim |
| Título parcial | Philosopher's Stone | Harry Potter and the Philosopher's Stone | Mesmo título | Mesmo título | Sim |
| Erro OCR simulado | The Hobit | The Hobbit | The Hobbit | The Hobbit | Sim |
| Título | Hamlet | Hamlet | Hamlet | Hamlet | Sim |
| Autor | J. R. R. Tolkien | The Hobbit | Tolkien | The Hobbit | Sim |
| ISBN-13 | 9780547928227 | The Hobbit | The Hobbit | The Hobbit | Sim |

Na execução pareada registrada, a versão anterior respondeu em 9/9 casos, com Top-1 correto em 8/9, Recall@3 em 8/9 e mediana de 1,278 s. A versão atual respondeu em 9/9, com Top-1 correto em 9/9, Recall@3 em 9/9 e mediana de 1,096 s. Para `The Hobit`, a consulta estrita encontra um material educacional parecido; o fallback amplo recupera `The Hobbit`, e o ranqueamento por similaridade de título o coloca em primeiro lugar. O teste de regressão reproduz esse caso com respostas simuladas. Em consultas ao vivo, a API pode mudar a ordem ou os registros retornados. Uma tentativa exploratória anterior para The Hobbit sofreu timeout de conexão em 13,019 s; ela não foi substituída por resultado fictício. A amostra pequena e selecionada não estima precisão de produção.

## Comparação com a versão anterior

A versão anterior de `backend.catalogo` oferecia consulta genérica por `q` e campos reduzidos, sem escolha de busca por autor ou ISBN. O script atual reproduz essa consulta legada e compara cada caso com a busca tipada, usando a mesma API e manifesto. Nesta rodada, a busca por autor e o fallback tolerante elevaram os acertos observados; as métricas são descritivas desta execução, não uma estimativa estatística nem garantia de melhoria geral. O fallback pode exigir uma segunda chamada à Open Library quando nenhum resultado estrito alcança similaridade 90, elevando a latência desses casos.

## Resposta da Open Library no caso visual

O teste Edge de ponta a ponta consultou a Open Library durante o reconhecimento real da capa The Hobbit. O OCR recuperou o título e o autor; o primeiro candidato foi The Hobbit por J.R.R. Tolkien, com pontuação heurística 100/100. A resposta também continha outras edições/obras com título semelhante, mantidas como escolhas separadas. A pontuação não é probabilidade.

## Google Books

O provedor Google Books foi mantido desligado porque `GOOGLE_BOOKS_API_KEY` não está configurada localmente. Testes simulados confirmaram que o provedor não envia requisição sem configuração, que timeout/JSON inválido viram erro controlado e que complementação exige ISBN exato. A consulta real ao serviço Google Books não foi executada.

## Limitações

O conjunto automatizado de regressão não é um benchmark de catálogo calibrado. Para comparar antes/depois, o mesmo conjunto de títulos conhecidos, consultas e limites deverá ser aplicado aos dois comportamentos. Cobertura, variação de dados, ordenação do serviço e disponibilidade da rede influenciam os resultados.
