# Open Library

A Open Library é a fonte primária do catálogo. O adaptador consulta `GET /search.json`, limita o número de resultados, usa timeout HTTP e aplica intervalo global entre requisições. A chave de busca informa título, autor, ISBN ou assunto; ISBN é normalizado antes da consulta. Os campos retornados passam por validação de tipo e limite antes de formar o JSON da interface.

O serviço distingue obras (`OL...W`) e edições (`OL...M`). A busca em nível de obra pode expor ISBNs e dados de edições agregados. A aplicação mantém a chave de obra como identidade do candidato e não presume que um campo agregado represente a edição fotografada. O OCR continua sujeito a confirmação humana e a pontuação não é probabilidade.

O cache em memória tem máximo de 256 combinações e validade de uma hora. Erros não são convertidos em resultados vazios. A rota comunica indisponibilidade como HTTP 503; o fluxo de OCR preserva o texto reconhecido para busca manual. O programa não faz scraping nem baixa URL de capa no servidor.

O User-Agent atual identifica o projeto, mas não contém email de contato. A política oficial recomenda identificação para uso regular; o limite identificado só deverá ser solicitado quando um contato real do projeto puder ser configurado, sem inventar endereço. A política publicada informa limites por segundo para tráfego identificado e não identificado, sujeitos à política vigente.

Referências oficiais: [API e política de uso](https://openlibrary.org/developers/api), [Search API](https://openlibrary.org/dev/docs/api/search).
