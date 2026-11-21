# Testes e verificações

## Etapa 9 — página ODS, progresso, metas e recomendações

Em 20/11/2026, a suíte integral atualizada executou **78 testes aprovados em 57,667 s**, com `BIBLIOTECA_DATABASE_NAME=biblioteca_inteligente_test`. A execução cobriu página ODS pública e navegação, quatro perguntas do professor, progresso de leitura, validação de páginas/datas, metas CRUD e contagem de conclusões, preferências, recomendações, CSRF, sessões, isolamento por usuário e integrações PostgreSQL. A primeira execução completa revelou falha ao excluir uma associação com progresso; o repositório passou a remover explicitamente o progresso da associação antes da exclusão. O teste PostgreSQL isolado e a suíte integral subsequente passaram.

Também passaram `compileall`, `pip check` (sem dependências quebradas), `node --check static/app.js` e `node --check static/auth.js`. Não foi necessária migração: os modelos e as tabelas existentes já suportavam as novas operações. As revisões Alembic dos bancos principal e de teste permaneceram inalteradas.

O Playwright com Microsoft Edge executou novamente a página ODS e o fluxo de biblioteca nas resoluções 1365 × 900 e 390 × 844. O fluxo validou OCR real com capa local, candidato bibliográfico, pesquisa pessoal, filtros, ordenação, detalhes, favorito, observação, progresso, meta, interesse, persistência, isolamento e remoção. A execução final está em `scripts/verificar_ui_etapa9.py`; as capturas estão em `docs/evidencias/etapa9-ods-notebook.png`, `docs/evidencias/etapa9-ods-celular.png`, `docs/evidencias/etapa9-biblioteca-notebook.png` e `docs/evidencias/etapa9-biblioteca-celular.png`. A inspeção não observou rolagem horizontal indevida nas duas resoluções.

A página pública `/sobre-ods` apresenta a ODS 4, a relação indireta proposta com a meta 4.6, as quatro respostas exigidas, o funcionamento e as limitações. As referências oficiais estão na própria página e em `docs/ODS_E_JUSTIFICATIVA.md`. Não houve pesquisa com participantes nem medição de impacto educacional.

O banco principal não foi usado para os testes de escrita. Nenhuma migração foi criada ou aplicada nesta etapa. A consulta somente de leitura ao banco de teste após a execução encontrou dois usuários, dois livros e uma associação preexistentes; como a origem desses registros não foi identificada, eles foram preservados. As novas contas de teste desta execução foram removidas pelo fluxo de limpeza e não aparecem no inventário. Permanecem pendentes a validação acadêmica definitiva da meta 4.6, evidências locais sobre o problema, contribuições reais dos integrantes e homologação da webcam física.

## Etapa 7 — catálogo bibliográfico

Registro final: 68 testes aprovados em 32,694 s na base `biblioteca_inteligente_test`.

Em 20/11/2026, a suíte integral executou **68 testes aprovados em 32,171 s** com `BIBLIOTECA_DATABASE_NAME=biblioteca_inteligente_test`. Foram adicionados casos de normalização/proveniência, buscas por autor e ISBN, checksum de ISBN, deduplicação somente pela mesma chave Open Library, `Retry-After`, provedor Google desativado sem chave, timeout e JSON inválido, complemento exato por ISBN, validação de payload, persistência de metadados somente após confirmação e ordenação OCR por evidência de autoria. Os testes com provedores externos usam mocks; nenhum mock foi contabilizado como consulta real.

Também passaram `compileall`, `pip check` (sem dependências quebradas), `node --check static/app.js`, `node --check static/auth.js` e `alembic check`. A revisão Alembic foi aplicada primeiro na base de teste e, após backup custom validado com `pg_restore --list`, no banco principal. Ambos chegaram à revisão `9a7d31f2c4e8`; o backup pré-migração está em `postgres/backups/` e é ignorado pelo Git.

O Playwright com Microsoft Edge executou cadastro, login, OCR real da capa local do Hobbit, busca Open Library, seleção confirmada, gravação e recarga no PostgreSQL de teste, recomendação, logout, novo login, remoção e preservação da chave de armazenamento legado. As resoluções inspecionadas foram 1365×900 e 390×844. As capturas da execução final estão em `docs/evidencias/etapa7-biblioteca-notebook.png` e `docs/evidencias/etapa7-biblioteca-celular.png`, além de `etapa7-cadastro.png` e `etapa7-login.png`. A inspeção visual observou o novo seletor de tipo, dados de obra identificados como agregados e candidatos com autoria incompatível abaixo dos que correspondem ao texto.

`scripts/avaliar_catalogo.py` realizou nove consultas reais Open Library, incluindo títulos, consulta parcial, variação de acentuação, erro OCR, autor e ISBN. O resumo observado foi resposta 9/9, Top-1 8/9, Recall@3 8/9 e mediana HTTP de 1,154 s. A consulta `The Hobit` encontrou um material parecido e não a obra esperada. Uma tentativa exploratória adicional recebeu timeout de 13,019 s; outra tentativa posterior respondeu. Resultados e limites estão em `docs/AVALIACAO_CATALOGO.md`. Google Books permaneceu desativado por falta de chave; a integração real não foi testada.

`scripts/avaliar_ocr.py` também executou RapidOCR real sobre a imagem local; título e autor foram recuperáveis, e “The Hobbit” por J.R.R. Tolkien apareceu em primeiro lugar. A mediana aquecida foi 1,847 s nesta execução. O registro dessa avaliação está em `docs/AVALIACAO_OCR.md`.

O banco principal foi consultado somente para leitura após a migração e manteve zero usuários, livros e associações; a base de teste também terminou sem registros de domínio. A webcam física continua sem homologação. As verificações acadêmicas de evidências ODS 4, meta 4.6 e contribuições dos integrantes permanecem abertas.

## Ambiente

- Windows 11 x64, build 26300; Python 3.12.10 no `.venv`.
- PostgreSQL portátil 17.12 em `127.0.0.1:5433`; uma instalação externa PostgreSQL 18.6 continua independente na porta 5432.
- SQLAlchemy 2.1.9, Alembic 1.20.1 e Psycopg 3.3.9 instalados somente no ambiente virtual. A [documentação SQLAlchemy 2](https://docs.sqlalchemy.org/en/20/intro.html) suporta CPython 3.7 ou superior; a [documentação Alembic](https://alembic.sqlalchemy.org/en/latest/front.html) inclui SQLAlchemy; a [documentação Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/install.html) declara suporte oficial a Python 3.10–3.15, PostgreSQL 10–18 e Windows.
- A série PostgreSQL 17.12 foi baixada da [distribuição binária EDB indicada pelo PostgreSQL](https://www.postgresql.org/download/windows/) e listada na [página oficial de binários EDB](https://www.enterprisedb.com/download-postgresql-binaries). A página não publicou checksum oficial para o ZIP. O SHA-256 calculado localmente foi `520c8c6f19abb3b31fa83ec5e486e2f769eedd7593d94e60a7cda8a5bfb4df91`; a verificação CRC do ZIP também passou. Esse hash não é apresentado como checksum oficial.

Após as migrações, `scripts/instalar_ambiente.ps1` foi executado novamente. O ambiente virtual, cluster e credenciais existentes foram preservados, a autenticação foi confirmada e o OCR local reconheceu texto sem acesso à internet. O verificador atualizado também confirmou dependências, versão do banco, privilégio de schema, revisão Alembic head e disponibilidade dos modelos.

## Estado anterior às migrações

O banco principal `biblioteca_inteligente` existia, pertencia à role `biblioteca_app` e não tinha tabelas de usuário. A base `biblioteca_inteligente_test` ainda não existia. A conta da aplicação não possuía SUPERUSER, CREATEDB ou CREATEROLE; autenticação SCRAM e listener loopback foram confirmados. A instalação PostgreSQL 18.6 não foi alterada.

Antes das mudanças no banco principal, foi criado o dump customizado `postgres/backups/biblioteca_inteligente-20261120-152457.dump`, cujo índice foi lido com `pg_restore --list`. O dump `postgres/backups/biblioteca_inteligente-20261120-153141.dump` foi criado antes da revisão final de privilégios; o backup posterior ao esquema completo é `postgres/backups/biblioteca_inteligente-20261120-154122.dump`. Os dois índices tinham 40 entradas e foram lidos com `pg_restore --list`. A restauração de backup não foi executada.

## Migrações aplicadas

As revisões Alembic `b86bc6695616`, `766b3c6df106` e `887b2bb10d3d` foram aplicadas primeiro na base de testes e depois no banco principal, após a inspeção de que o principal não tinha tabelas nem dados de negócio. Os dois bancos chegaram à revisão `887b2bb10d3d`.

O schema público contém sete tabelas contando `alembic_version` e as seis tabelas de domínio. As contas de runtime não possuem CREATE no schema. A role administrativa é proprietária dos bancos e das tabelas; `biblioteca_app` recebeu conexão, uso do schema e DML. A role do Flask continua separada da configuração Alembic e não recebe autoridade administrativa.

O banco principal terminou com seis tabelas de domínio e zero registros de negócio. A coleção `estante-livros-v1` não foi consultada, alterada ou importada. A base de testes recebeu somente dados transacionais revertidos pela suíte e um marcador isolado de persistência, removido após a verificação.

## Suíte executada

Com o PostgreSQL local iniciado, foi executado:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado observado: **37 testes aprovados** (26 testes Flask e contratos existentes, mais 11 testes de integração PostgreSQL). Os testes de banco usam `biblioteca_inteligente_test`, aplicam `alembic upgrade head` de forma idempotente e revertem os registros temporários em transações. Nenhum caso de teste limpa o banco principal.

Os casos reais exercitam conexão autenticada, revisão e tabelas, hashes de senha, username normalizado e único, livro sem ISBN, duplicatas de ISBN/identificador externo, títulos repetidos de edições distintas, CHECK constraints de ISBN e JSONB, chaves estrangeiras, bibliotecas por proprietário, remoção segura, progresso, metas, preferências, validações, falha de conexão e ausência de privilégio CREATE para o runtime.

Também passaram:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py backend tests scripts migrations
.\.venv\Scripts\python.exe -m pip check
node --check static/app.js
.\.venv\Scripts\python.exe -m alembic check
```

`alembic check` foi executado no banco de testes e no principal e não encontrou operações pendentes. `scripts/verificar_migracoes.py` confirmou a revisão head do principal sem alterar dados. A ferramenta `alembic check` não compara todas as diferenças de CHECK constraints; por isso, as verificações de ISBN e JSONB constam como operações explícitas na segunda revisão e têm testes PostgreSQL.

## Persistência após reinicialização

`scripts/testar_persistencia_postgres.py` gravou usuário, livro e associação com identificador descartável somente em `biblioteca_inteligente_test`. O PostgreSQL do projeto foi parado pelo script controlado, reiniciado e consultado em conexão nova. Conta, livro e associação permaneceram disponíveis; a fase `--limpar` removeu os registros da mesma base de testes. O banco principal e as outras instalações não foram usados nesse teste.

## Aplicação e OCR

Os 26 testes anteriores cobrem rotas Flask, respostas JSON, uploads, contratos do JavaScript e chave local. Nesta etapa, o servidor real foi iniciado por `scripts/executar_flask.py`; as rotas `/`, `/api/health`, `/static/style.css` e `/static/app.js` responderam HTTP 200. O processo foi encerrado pelo sinal local controlado, sem abrir navegador. Nenhum repositório PostgreSQL foi ligado a uma rota. A verificação visual e OCR com capas reais, Open Library e navegador descritas na Etapa 2 permanecem como histórico.

## Limitações e pendências

- A webcam física não foi homologada; o teste de câmera virtual da Etapa 2 não comprova o dispositivo do notebook.
- Evidências locais para o problema ligado à ODS 4, validação acadêmica da meta 4.6 e contribuições reais dos integrantes continuam pendentes.
- A aplicação não executa CRUD PostgreSQL via HTTP, não possui login e mantém a biblioteca no `localStorage`.
- A restauração de dump ainda não foi testada; os backups foram criados e o índice lido.
- Os resultados de Open Library dependem da internet; os testes automatizados usam mocks.

## Etapa 5 — autenticação e persistência por conta

Na revisão da Etapa 5, a suíte automatizada executou **45 testes aprovados** em 20,610 segundos. Os testes utilizam `biblioteca_inteligente_test`; as contas e livros temporários do conjunto de rotas são removidos ao final. A cobertura inclui cadastro/validação, duplicidade canônica, verificação de hash Werkzeug, login e mensagem genérica, limitação temporária, cookie/sessão, CSRF ausente/inválido, logout, páginas e APIs privadas, falha controlada do banco, rejeição de redirecionamento externo, associação idempotente, isolamento entre duas contas e remoção limitada ao proprietário. Os 11 testes existentes de repositórios PostgreSQL também passaram.

Foi executado `scripts/verificar_ui_etapa5.py` com Playwright e Microsoft Edge já instalado. O navegador completou o cadastro, verificou a validação visual de confirmação de senha, iniciou sessão, enviou uma imagem real de capa do Hobbit recortada da evidência OCR anterior, recebeu texto real do RapidOCR, consultou a Open Library, associou o resultado, atualizou a página, saiu, entrou novamente, confirmou persistência e removeu o livro. O contexto efêmero continha um registro legado artificial; o aviso apareceu e o valor permaneceu idêntico após recarga, sem importação. O roteiro limpou a conta descartável e os registros bibliográficos órfãos que criou no banco de teste. Recomendações reais foram solicitadas a partir da conta; a resposta foi recebida sem estado visual de erro.

As capturas sem credenciais foram gravadas em `docs/evidencias/etapa5-cadastro.png`, `etapa5-login.png`, `etapa5-biblioteca-notebook.png` e `etapa5-biblioteca-celular.png`. As resoluções verificadas foram 1365×900 e 390×844. A capa de teste veio de uma captura existente, não de uma fotografia nova feita durante a Etapa 5. A webcam física não foi acessada nesta rodada; a verificação anterior usou câmera virtual. A fonte Google Fonts e capas externas dependem de internet e podem aparecer com fontes de fallback ou marcadores quando o serviço não responde.

Também foram executados após as alterações:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py backend tests scripts migrations
.\.venv\Scripts\python.exe -m pip check
node --check static\app.js
node --check static\auth.js
```

`compileall`, `pip check` e a verificação de sintaxe JavaScript terminaram com código zero. `scripts/verificar_migracoes.py` confirmou que o banco principal permanece em `887b2bb10d3d`; nenhum esquema ou dado de negócio do principal foi alterado nesta etapa. `scripts/diagnosticar_banco.py` confirmou todas as contagens do banco principal em zero. A conta de teste é limpa depois do roteiro visual e da suíte.

O script visual depende de Playwright já disponível no `.venv`, Edge instalado e Open Library acessível. Ele restringe suas conexões ao banco `biblioteca_inteligente_test`; não deve ser apontado ao banco principal.

Na execução final após a correção de uma expectativa de ordenação não determinística nos testes existentes, os mesmos **45 testes** passaram em 22,313 segundos. A primeira duração registrada acima corresponde à execução anterior igualmente aprovada.

Após a revisão de formatação, a execução integral mais recente repetiu os **45 testes**, todos aprovados em 21,158 segundos.

Na conferência final do cluster local ativo, os **45 testes** passaram novamente em 19,573 segundos.

## Histórico substituído pela Etapa 5

As frases acima em “Estado anterior às migrações”, “Suíte executada” e “Limitações” descrevem a Etapa 4. Na Etapa 5, cadastro, login e persistência inicial de livros por conta passaram a usar as rotas Flask e PostgreSQL. O histórico de 37 testes permanece registrado como resultado da etapa anterior; a execução atual da Etapa 5 é de 44 testes.

Nenhuma credencial é registrada nesta documentação. `.env`, dados PostgreSQL, ambiente virtual, binários e backups continuam excluídos pelo `.gitignore`.

## Etapa 6 — OCR e integração visual

O conjunto controlado reutiliza uma capa real já existente na evidência do projeto, recortada para `tests/fixtures/ocr/hobbit-capa-evidencia.png`. Não havia dez imagens separadas e autorizadas na pasta; por isso, a avaliação contém somente uma capa e não sustenta métricas gerais.

Foi executado `scripts/avaliar_ocr.py` com RapidOCR 3.10.0 e modelos locais. No ensaio bem-sucedido, o título “The Hobbit” e o autor foram recuperáveis; a chamada autenticada à rota retornou o título correto em primeiro lugar, pontuação heurística 99,0, e mediana de inferência aquecida de 1,704 s em três execuções. O fluxo anterior, reconstituído com o mesmo texto OCR e as antigas consultas, não gerou candidato acima do limiar. Uma execução posterior do script de avaliação recebeu timeout da Open Library, preservou o resultado OCR e registrou a falha. O serviço externo, portanto, não ficou uniformemente disponível durante toda a rodada.

Variantes de pré-processamento em escala de cinza, nitidez e ampliação foram comparadas na mesma imagem. Todas apresentaram tempo maior e/ou texto menos limpo que RGB com contraste 1,18; nenhuma foi ativada. Os números e critérios estão em `docs/AVALIACAO_OCR.md`; a pontuação heurística não é probabilidade.

Foram adicionados testes para ordenação espacial pelas caixas RapidOCR, confiança não finita, confiança na priorização de consultas, reforço limitado por autor, palavras funcionais isoladas em títulos, imagem vazia e degradada com inferência real, dimensões acima do limite, timeout de catálogo e filtragem de candidatos fracos. A suíte histórica tinha 45 testes; a execução integral final da Etapa 6 executou **55 testes, todos aprovados em 32,869 s**. Os testes PostgreSQL continuam utilizando exclusivamente `biblioteca_inteligente_test`, que terminou com zero usuários, livros e associações de biblioteca.

O fluxo visual foi executado no Edge com Playwright em 1365×900 e 390×844, utilizando servidor Flask iniciado com a base de testes: cadastro, login, OCR real, candidatos Open Library originados da resposta OCR, adição confirmada, persistência após recarga, recomendações, logout, novo login e remoção. As capturas estão em `docs/evidencias/etapa6-cadastro.png`, `etapa6-login.png`, `etapa6-biblioteca-notebook.png` e `etapa6-biblioteca-celular.png`. As imagens foram inspecionadas; a disposição responsiva permaneceu consistente e a pontuação é rotulada como heurística `n/100`, sem símbolo de porcentagem.

O servidor Flask iniciado para a validação foi encerrado graciosamente. O cluster PostgreSQL do projeto já estava ativo antes do teste e permaneceu ativo; nenhuma migração foi executada. A webcam física não pôde ser enumerada porque o acesso CIM do Windows foi negado. A homologação manual descrita em `docs/VISAO_COMPUTACIONAL.md` continua necessária.

## Etapa 7 — catálogo e metadados

Após a integração bibliográfica, `python -m unittest discover -s tests -q` foi executado no ambiente virtual, com `BIBLIOTECA_DATABASE_NAME=biblioteca_inteligente_test`: **69 testes aprovados em 31,292 s**. A suíte inclui o fallback de título para erros de OCR; as verificações de banco continuam isoladas na base de testes. O ensaio real pareado `scripts/avaliar_catalogo.py` consultou nove casos na busca legada e na atual. Na execução registrada em `docs/AVALIACAO_CATALOGO.md`, a versão anterior obteve 8/9 no Top-1 e Recall@3, e a versão atual 9/9 em ambas as métricas; medianas observadas: 1,278 s e 1,096 s, respectivamente. A API é variável, a amostra é pequena, e esses valores não representam precisão geral. O Google Books permaneceu sem consulta real por ausência de chave local.

Após os ajustes finais, o roteiro `scripts/verificar_ui_etapa5.py` foi executado no Edge com a aplicação Flask ligada exclusivamente a `biblioteca_inteligente_test`. O roteiro verificou cadastro, login, reconhecimento OCR real, busca Open Library, inclusão confirmada, persistência após recarga, recomendações, logout, novo login, remoção e preservação da chave legada do `localStorage`. As capturas foram atualizadas em `docs/evidencias/etapa7-*.png`. Viewports 1365×900 e 390×844 passaram sem rolagem horizontal. A inspeção identificou e corrigiu um excesso de 2 px causado por tamanho mínimo intrínseco nas grades internas. O servidor de teste encerrou a escuta após o roteiro; um processo local remanescente da execução foi encerrado pelo PID exato que havia sido iniciado para esse teste.

## Etapa 8 — biblioteca pessoal

A migração `c4e8a19f07d2` foi aplicada primeiro à base `biblioteca_inteligente_test`. `alembic current` confirmou essa revisão como head e `alembic check` não encontrou divergências. Antes da atualização do banco principal, `scripts/backup_postgres.ps1` criou um dump customizado datado; `pg_restore --list` confirmou o formato e os itens do arquivo. A migração aditiva foi então aplicada ao banco principal, `scripts/verificar_migracoes.py` confirmou o head `c4e8a19f07d2` e novo `alembic check` terminou sem diferenças. Nenhum downgrade ou restauração foi executado.

A execução integral `\.venv\Scripts\python.exe -m unittest discover -s tests -v` concluiu **74 testes aprovados em 49,565 s**, com PostgreSQL de teste real. A cobertura nova inclui busca combinada, acentos/ISBN, filtros, ordenação, paginação, totais por conta, detalhes, favorito, observações, CSRF, limites do banco e isolamento do proprietário. `compileall`, `pip check`, `node --check static/app.js` e `node --check static/auth.js` também foram executados; `pip check` reportou nenhuma dependência quebrada e as verificações de sintaxe finalizaram sem erros.

O roteiro `scripts/verificar_ui_etapa8.py` passou no Edge/Playwright usando a base de teste, OCR real, catálogo Open Library, autenticação, inclusão, filtros combinados, favorito, detalhes, observações, persistência após recarga, ISBN, ordenação, duas páginas, recomendações, isolamento e remoção. As capturas `docs/evidencias/etapa8-biblioteca-notebook.png` (1365×900) e `docs/evidencias/etapa8-biblioteca-celular.png` (390×844) foram inspecionadas visualmente; os controles permanecem utilizáveis e não foi observada rolagem horizontal indevida. Os screenshots contêm somente a conta ficcional criada para o roteiro.

O navegador de teste não dependeu da webcam física. A captura webcam efetiva continua condicionada à homologação manual descrita em `docs/VISAO_COMPUTACIONAL.md`. O roteiro visual executou as ações de teste apenas na base `_test` e removeu a conta temporária ao terminar; nenhuma biblioteca real foi apagada.

## Etapa 10 — revisão final

Na revisão final, a suíte completa executou **78 testes aprovados em 51,720 s**, usando `biblioteca_inteligente_test`. Também foram aprovados `compileall`, `pip check`, `node --check` para `static/app.js` e `static/auth.js`, `git diff --check` e `alembic check` nos bancos principal e de teste. A revisão Alembic permaneceu em `c4e8a19f07d2`; nenhuma migração foi necessária.

O PostgreSQL portátil 17.12 autenticou os acessos locais, verificou a conta de aplicação sem privilégios administrativos e confirmou que o diretório de dados corresponde à instância deste projeto. `scripts/verificar_ambiente.ps1` aprovou os componentes configurados e executou OCR local com acesso à rede bloqueada. O dump `biblioteca_inteligente-20261120-201929.dump` foi listado com `pg_restore` e restaurado em `biblioteca_inteligente_restore_20261120`, uma base nova e isolada. A restauração confirmou sete tabelas e a revisão `c4e8a19f07d2`. O banco principal continuou sem registros de negócio. O inventário da Etapa 9 documentava dois usuários, dois livros e uma associação em `_test`; a verificação final encontrou zero registros de domínio nessa base. A causa dessa diferença não foi determinada, não havia dump de `_test` disponível e nenhum dado foi restaurado ou reconstruído sem fonte verificável.

O OCR real em `tests/fixtures/ocr/hobbit-capa-evidencia.png` recuperou o texto `HOBBIT` e o autor `JRRTOLKIEN`; a mediana observada foi 1,694 s. O ensaio foi executado com `--sem-catalogo`, portanto não mediu identificação bibliográfica nem disponibilidade externa. A capa constitui uma amostra única e não sustenta uma taxa geral de precisão.

O servidor Flask respondeu em `/api/health` e `/sobre-ods` com HTTP 200. O roteiro `scripts/verificar_ui_etapa9.py` foi executado no Microsoft Edge com Playwright, usando a base isolada; verificou OCR real, candidato, biblioteca, filtros, ordenação, paginação, detalhes, favorito, observação, progresso, meta, preferências, persistência, isolamento de conta e os viewports 1365×900 e 390×844. As capturas geradas pelo roteiro que contêm estado de teste permanecem locais e são ignoradas pelo Git.

Uma falha de abertura de URL pelo navegador padrão no `INICIAR.bat` foi reproduzida como erro de associação do Windows. `scripts/iniciar.ps1` foi ajustado para abrir o Edge instalado diretamente e manter o navegador padrão como fallback. Após o ajuste, a chamada ao script confirmou PostgreSQL e Flask ativos, e a rota de saúde voltou a responder HTTP 200.

O encerramento gracioso e a reinicialização da instância do projeto foram confirmados com elevação local, necessária neste ambiente para controlar o processo PostgreSQL. A webcam física não foi homologada; apenas testes de câmera virtual já constavam do histórico. A validação física permanece manual. As pendências acadêmicas sobre evidências do problema, adequação definitiva à meta 4.6 e contribuições reais dos integrantes também permanecem abertas.

## Atualização de hospedagem e experiência de detalhes — 21/11/2026

A suíte foi executada novamente em `.venv`, com `BIBLIOTECA_DATABASE_NAME=biblioteca_inteligente_test`: **81 testes Python aprovados em 44,894 s**. Quatro testes Node.js passaram em `tests/test_formatters.js`, cobrindo offsets ISO equivalentes, UTC, microssegundos, valores ausentes/inválidos e rótulos bibliográficos conhecidos. Também passaram `node --check` para `static/app.js` e `static/formatters.js`, `pip check` e `compileall` de aplicação, backend, migrações e scripts.

O roteiro visual local `scripts/_visual_validate.py`, executado no Microsoft Edge/Playwright com a base de teste, confirmou CSS e formatador carregados, classificação individual, filtro por origem, clique no card e teclado, botões de favorito/remoção independentes, detalhes com datas `DD/MM/AAAA às HH:mm`, idioma e catálogo legíveis, página ODS pública, nenhuma rolagem horizontal em 1365×900 ou 390×844 e nenhum erro JavaScript no navegador. As capturas foram mantidas apenas em `runtime/`, diretório local ignorado pelo Git.

O RapidOCR real continuou sendo exercitado pelos testes com imagem em branco e imagem de baixa qualidade; a suíte de regressão também manteve a verificação anterior da capa `The Hobbit`. A etapa corrente não repetiu uma comparação ampla de precisão com novas capas. A branch isolada Neon `preview` recebeu as migrações do esquema até `d1a45f8c2e70`; ainda não houve implantação Vercel nem teste HTTP online. Portanto, autenticação hospedada, OCR hospedado e persistência online permanecem pendentes de build e homologação reais.
