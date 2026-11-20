# Regras permanentes do projeto

## Linguagem e documentação

- Toda documentação, explicação técnica, comentário, docstring, relatório de alteração e descrição de teste deve ser redigida em terceira pessoa, com redação impessoal quando apropriado.
- A interface deve priorizar redação impessoal ou em terceira pessoa quando isso soar natural. Identificadores e sintaxe não devem ser alterados apenas para cumprir essa regra.
- Os comentários devem explicar decisões e etapas relevantes, ser didáticos e corresponder ao comportamento efetivo. Comentários triviais, genéricos ou desatualizados não devem ser adicionados.
- Cada função Python deve possuir docstring que explique objetivo, parâmetros, retorno, responsabilidade, integrações e tratamento de erros relevante.
- A documentação das integrações deve relacionar HTML e seus elementos, CSS, JavaScript e eventos, rota Flask, função Python, banco ou API externa, resposta e atualização da interface. O mapa deve descrever o código existente.
- Seções HTML importantes devem documentar finalidade, elementos e IDs/classes, CSS, JavaScript e relação com o backend. Comentários CSS devem identificar elementos, cores, dimensões, espaçamentos, responsividade e estados visuais pertinentes. Docstrings ou comentários JavaScript devem explicar eventos, dados, alterações no HTML, requisições, rotas, respostas e erros.

## Segurança e dados

- Segredos, credenciais, tokens, conteúdo real de `.env`, dados privados, bancos com dados e backups não devem ser expostos em documentação nem publicados no Git.
- Senhas devem ser armazenadas somente com hash seguro. A aplicação futura deve manter o PostgreSQL local sem exposição à rede externa.
- Uploads, entradas, permissões e erros devem ser validados e tratados sem revelar informações confidenciais.
- Ações destrutivas, publicação e alterações de dados não devem ser executadas sem autorização explícita. Scripts não devem apagar dados automaticamente.
- O projeto deve usar PostgreSQL como banco definitivo; SQLite não deve ser introduzido como substituto.

## Qualidade e preservação

- Funcionalidades existentes devem ser preservadas. Remoções ou mudanças incompatíveis exigem justificativa e autorização.
- Cada alteração deve revisar sintaxe, formatação, comentários, segurança, tratamento de erros, organização, integrações, integridade dos dados, HTML, CSS, responsividade, JavaScript, regressões e testes automatizados disponíveis.
- Relatórios devem distinguir verificações executadas de verificações propostas. Testes não devem ser declarados executados sem execução observada.
- Pendências críticas conhecidas impedem declarar uma etapa futura concluída.
- Etapas autorizadas devem ser respeitadas. A análise inicial não autoriza implementação, instalação, migração, publicação ou execução de scripts que alterem dados.
