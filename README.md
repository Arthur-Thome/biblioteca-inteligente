# Biblioteca Inteligente

## Catálogo bibliográfico (Etapa 7)

A busca manual permite selecionar título, autor ou ISBN. A Open Library permanece como fonte principal; Google Books é opcional e só preenche metadados ausentes quando há ISBN idêntico. Para habilitar o provedor complementar, a chave oficial pode ser configurada em `GOOGLE_BOOKS_API_KEY` no `.env` local; sem a chave, a função segue somente com Open Library. Nenhuma chave deve ser inserida no README ou versionada.

Os resultados podem exibir subtítulo, autores, editora, idioma, ano, páginas, ISBN, descrição e proveniência quando as fontes fornecem esses dados. Ausências não são estimadas. A pontuação heurística não é uma probabilidade e a confirmação do candidato continua obrigatória. A migração `9a7d31f2c4e8` acrescenta `livros.metadados` sem transferir ou remover registros existentes.

Detalhes estão em [docs/CATALOGO_BIBLIOGRAFICO.md](docs/CATALOGO_BIBLIOGRAFICO.md), [docs/OPEN_LIBRARY.md](docs/OPEN_LIBRARY.md), [docs/GOOGLE_BOOKS.md](docs/GOOGLE_BOOKS.md) e [docs/METADADOS_LIVROS.md](docs/METADADOS_LIVROS.md).

Protótipo acadêmico local para reconhecer texto em capas, pesquisar candidatos bibliográficos, organizar uma coleção individual no PostgreSQL e recomendar obras por assuntos relacionados.

## Objetivo e escopo

O sistema demonstra visão computacional aplicada à leitura de capas por OCR. O RapidOCR extrai texto; uma busca bibliográfica sugere candidatos e a pessoa usuária confirma o título. A recomendação atual compara assuntos de catálogo. O protótipo apoia organização e descoberta de leituras, mas não comprova melhoria de alfabetização nem treina um modelo próprio de classificação de livros.

A ODS 4 e a meta 4.6 permanecem propostas a validar. O roteiro do professor exige problema real ligado a uma ODS e meta, descrição do público afetado e importância do problema, justificativa da solução e da IA, sistema com interface e operação ponta a ponta, repositório com README, demonstração ao vivo e participação de todos os integrantes no desenvolvimento e na apresentação. O roteiro recomenda priorizar problema concreto, se possível relacionado à realidade local do grupo.

A organização e a descoberta de leituras podem oferecer apoio potencial a práticas de leitura, mas ainda não foi demonstrada relação causal com alfabetização ou com o indicador da meta 4.6. O grupo deverá documentar evidências locais, público afetado e critérios de avaliação antes de afirmar adequação ou impacto. Nomes e contribuições dos integrantes devem refletir a participação efetivamente realizada; esses dados ainda precisam ser definidos pelo grupo.

## Contexto acadêmico e ODS

A ODS inicialmente escolhida é a ODS 4 — Educação de Qualidade, com relação proposta e indireta à meta 4.6. O problema proposto envolve tarefas de organização de bibliotecas pessoais, acompanhamento de leituras e descoberta de livros. A prevalência desse problema entre o público local ainda não foi investigada. O Censo Demográfico do IBGE contextualiza a alfabetização no Brasil, mas não demonstra que a dificuldade de organizar leituras cause analfabetismo nem que a aplicação altere indicadores educacionais. A funcionalidade e a justificativa estão detalhadas em [docs/ODS_E_JUSTIFICATIVA.md](docs/ODS_E_JUSTIFICATIVA.md) e na página pública `/sobre-ods`.

Fontes institucionais: [ONU Brasil — ODS 4](https://brasil.un.org/pt-br/sdgs/4), [ONU — Goal 4](https://sdgs.un.org/goals/goal4) e [IBGE Educa — Alfabetização](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html). A adequação acadêmica definitiva da meta, evidências locais e qualquer impacto educacional permanecem pendentes.

## Integrantes e contribuições

Os nomes dos integrantes e suas contribuições efetivas ainda não foram confirmados para esta documentação. O grupo deverá preencher `docs/APRESENTACAO.md` com informações verificadas antes da entrega acadêmica; nenhum nome ou tarefa deve ser presumido.

## Tecnologias

- Python 3.12 e Flask.
- HTML, CSS e JavaScript.
- Pillow, NumPy, RapidOCR, ONNX Runtime e RapidFuzz.
- Open Library Search API como catálogo principal e adaptador opcional Google Books por correspondência exata de ISBN.
- Cadastro e autenticação de contas com senhas em hash Werkzeug.
- PostgreSQL local para contas e livros associados individualmente.
- `localStorage` legado preservado sem importação automática.
- SQLAlchemy 2, Alembic e Psycopg 3 para a camada PostgreSQL versionada.
- Testes `unittest` com cliente de teste Flask e mocks.

PostgreSQL 17.12 está preparado como instância portátil local e possui migrações para contas, catálogo, bibliotecas, progresso, metas e preferências, incluindo metadados complementares e dados pessoais da coleção. Cadastro, login, gerenciamento da biblioteca, progresso, metas e preferências estão integrados às rotas e repositórios. A página pública `/sobre-ods` explica a relação proposta à ODS 4 e suas limitações. Importação do `localStorage` e recomendações baseadas em modelo treinado continuam não implementados. Google Books está integrado como fonte complementar opcional, mas não foi testado em serviço real porque não há chave local configurada.

## Estrutura

```text
app.py                         ponto de entrada Flask
backend/__init__.py            fábrica e configuração da aplicação
backend/routes.py              endpoints HTTP e respostas JSON
backend/catalogo.py            cliente e normalização Open Library
backend/providers/             adaptador Google Books opcional
backend/visao_computacional.py preparação e OCR de imagem
backend/recomendacoes.py       seleção de assuntos e ranking
backend/validacoes.py          validação de uploads e JSON
backend/database.py            URL segura, engine e ciclo de sessão SQLAlchemy
backend/models.py              seis entidades relacionais do esquema inicial
backend/repositories/          operações transacionais por entidade
migrations/                    revisões versionadas Alembic
alembic.ini                    configuração sem credenciais
templates/login.html           formulário de acesso
templates/cadastro.html        formulário de cadastro
templates/index.html           biblioteca autenticada
templates/sobre_ods.html       justificativa pública da ODS 4
static/style.css               aparência e responsividade
static/app.js                  eventos, câmera, APIs e biblioteca PostgreSQL
static/auth.js                 validação de confirmação no cadastro
models_ocr/                    modelos RapidOCR locais, ignorados pelo Git
postgres/runtime/              binários PostgreSQL portáteis, ignorados pelo Git
postgres/data/                 cluster PostgreSQL local, ignorado pelo Git
postgres/logs/                 registros operacionais locais
postgres/backups/              dumps locais, ignorados pelo Git
scripts/                       preparação, inicialização, parada, verificação e backup
scripts/avaliar_catalogo.py    avaliação real reproduzível de busca bibliográfica
scripts/verificar_ui_etapa5.py inspeção opcional do fluxo visual com Playwright e Edge
tests/test_app.py              testes de rotas e contratos Flask
tests/test_database.py         testes PostgreSQL na base isolada _test
docs/                           arquitetura, integração, mapa e testes
docs/ODS_E_JUSTIFICATIVA.md     contexto, fontes e limites acadêmicos
docs/PROGRESSO_LEITURA.md      rotas e regras de acompanhamento
docs/METAS_LEITURA.md          CRUD e cálculo das metas pessoais
docs/RECOMENDACOES.md          critérios de sugestão bibliográfica
```

## Execução no Windows

O projeto utiliza Python 3.12 x64 e o ambiente virtual local `.venv`. Na primeira preparação, o comando instala dependências apenas nesse ambiente, copia os modelos OCR locais, cria credenciais aleatórias em `.env` protegido e inicializa o PostgreSQL do projeto uma única vez:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar_ambiente.ps1
```

Depois da preparação inicial, `INICIAR.bat` inicia somente o cluster identificado do projeto, verifica autenticação, inicia Flask e confirma `/api/health` antes de abrir `http://127.0.0.1:5000`. `PARAR.bat` solicita encerramento gracioso do Flask e parada smart do cluster do projeto. `VERIFICAR.bat` diferencia instalação, configuração e funcionamento dos componentes. Os arquivos de lote usam política de execução somente no processo PowerShell chamado e não alteram configurações globais.

O PostgreSQL do projeto usa `127.0.0.1:5433`; uma instalação PostgreSQL 18 externa encontrada no computador permanece independente. O cluster local não cria serviço permanente do Windows. Para executar um backup sem sobrescrever cópias anteriores:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_postgres.ps1
```

O ZIP dos binários e os modelos são mantidos na pasta do projeto e ignorados pelo Git. A instalação inicial do driver pode depender de acesso ao índice de pacotes; pesquisas e recomendações continuam dependendo da internet. O OCR foi verificado usando os modelos locais sem conexão. A câmera requer permissão do navegador e homologação física no notebook de apresentação.

## Fluxo de uso

1. A pessoa usuária cria uma conta ou entra por `/login`; as contas ficam separadas no PostgreSQL local.
2. Uma imagem JPG, PNG ou WEBP de até 8 MB é selecionada, ou uma captura é feita pela webcam.
3. O backend valida e prepara a imagem; RapidOCR extrai texto localmente.
4. Consultas derivadas do OCR ou digitadas manualmente são enviadas à Open Library.
5. A pessoa usuária confirma um dos candidatos; o Flask associa o livro à conta no PostgreSQL.
6. A biblioteca é carregada por `/api/library`; pesquisa pessoal, filtros, ordenação e paginação usam somente os livros daquela conta. Favoritos e observações pessoais são salvos na associação de biblioteca; detalhes e remoção continuam sob controle do proprietário autenticado.
7. A página pública `/sobre-ods` apresenta a justificativa acadêmica e as quatro perguntas exigidas no roteiro, sem alegar impacto educacional comprovado.
8. O diálogo de cada livro permite registrar status, páginas e datas; a área de metas conta conclusões no período. Preferências declaradas e favoritos influenciam sugestões heurísticas.

A imagem não é armazenada pelo protótipo. Consultas derivadas do OCR são enviadas à Open Library. Os dados antigos na chave `estante-livros-v1` são preservados e não são lidos, alterados ou importados; a interface informa que eles permanecem separados da nova conta. A senha não é armazenada no navegador.

## Testes e verificações

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar_postgres.ps1
.\.venv\Scripts\python.exe scripts\configurar_postgres.py --setup-test-db
$env:BIBLIOTECA_DATABASE_NAME = 'biblioteca_inteligente_test'
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:BIBLIOTECA_DATABASE_NAME
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app.py backend tests scripts migrations
node --check static/app.js
node --check static/auth.js
.\.venv\Scripts\python.exe scripts\avaliar_ocr.py
```

O comando de avaliação realiza OCR local e consulta a Open Library. Para medir somente o OCR com os modelos locais, o parâmetro `--sem-catalogo` evita a chamada externa.

`scripts/avaliar_catalogo.py` executa buscas curtas reais por título, autor e ISBN. A avaliação pareada registrada para a Etapa 7 está em [docs/AVALIACAO_CATALOGO.md](docs/AVALIACAO_CATALOGO.md); nesta amostra, a versão anterior acertou 8 de 9 no Top-1 e a atual 9 de 9. O ensaio inclui um erro OCR simulado, `The Hobit`, recuperado pelo fallback tolerante. A amostra é pequena e não estima precisão de produção.

Na Etapa 4, a suíte tinha 37 testes. A Etapa 5 amplia a cobertura de autenticação, CSRF, sessão e isolamento de biblioteca no banco PostgreSQL de teste. Os resultados atualizados constam em [docs/TESTES.md](docs/TESTES.md).

Na revisão final da Etapa 10, a execução integral mais recente aprovou **78 testes** na base isolada `biblioteca_inteligente_test`. `compileall`, `pip check`, verificações `node --check`, `alembic check`, a restauração de backup em base isolada, o OCR local sem catálogo externo e o roteiro de ponta a ponta com Edge/Playwright também foram executados. Os limites e resultados de cada verificação estão registrados em [docs/TESTES.md](docs/TESTES.md). A webcam física e a fundamentação acadêmica local permanecem pendentes de homologação pelo grupo.

## Segurança e limitações

- A autenticação utiliza sessão assinada, UUID conferido no PostgreSQL e CSRF em requisições que alteram dados.
- O upload tem limite de 8 MB; o backend verifica formato JPEG/PNG/WEBP e limita a imagem a 40 milhões de pixels.
- A recomendação é heurística por assuntos e depende da qualidade dos metadados da Open Library.
- O endpoint de saúde identifica serviços configurados, mas não confirma conectividade ou disponibilidade dos modelos.
- `.gitignore` exclui ambientes, credenciais locais, bancos, modelos e backups. Nenhum segredo real deve ser adicionado ao controle de versão.
- O cluster PostgreSQL continua local. Contas, dados bibliográficos, pesquisa pessoal, filtros, ordenação, paginação, favoritos, observações, progresso, metas e preferências estão integrados às rotas autenticadas. Recomendações heurísticas utilizam assuntos, favoritos e interesses declarados.

## Documentação

- [Arquitetura implementada](docs/ARQUITETURA.md)
- [Integração frontend/backend](docs/INTEGRACAO_FRONTEND_BACKEND.md)
- [Mapa do código](docs/MAPA_DO_CODIGO.md)
- [Testes e resultados](docs/TESTES.md)
- [Ambiente local](docs/AMBIENTE_LOCAL.md)
- [PostgreSQL portátil](docs/POSTGRES_PORTATIL.md)
- [Modelo de banco de dados](docs/BANCO_DE_DADOS.md)
- [Modelagem PostgreSQL](docs/MODELAGEM_POSTGRESQL.md)
- [Migrações Alembic](docs/MIGRACOES.md)
- [Gerenciamento da biblioteca](docs/BIBLIOTECA_PESSOAL.md)
- [Rotas e contratos de gerenciamento](docs/GERENCIAMENTO_LIVROS.md)
- [ODS 4 e justificativa acadêmica](docs/ODS_E_JUSTIFICATIVA.md)
- [Progresso de leitura](docs/PROGRESSO_LEITURA.md)
- [Metas de leitura](docs/METAS_LEITURA.md)
- [Recomendações](docs/RECOMENDACOES.md)
- [Guia de estudo do código](docs/GUIA_DE_ESTUDO.md)
- [Roteiro de apresentação](docs/APRESENTACAO.md)
- [Justificativa ODS e fontes](docs/ODS_E_JUSTIFICATIVA.md)
- [Plano futuro para localStorage](docs/PLANO_MIGRACAO_LOCALSTORAGE.md)
- [Cadastro e autenticação](docs/AUTENTICACAO.md)
- [Visão computacional](docs/VISAO_COMPUTACIONAL.md)
- [Avaliação do OCR](docs/AVALIACAO_OCR.md)
- [Catálogo bibliográfico](docs/CATALOGO_BIBLIOGRAFICO.md)
- [Open Library](docs/OPEN_LIBRARY.md)
- [Google Books](docs/GOOGLE_BOOKS.md)
- [Metadados bibliográficos](docs/METADADOS_LIVROS.md)
- [Avaliação do catálogo](docs/AVALIACAO_CATALOGO.md)
- [Sessões e segurança](docs/SESSOES_E_SEGURANCA.md)
- [Diagnóstico inicial](docs/DIAGNOSTICO_INICIAL.md)
- [Plano de migração](docs/PLANO_DE_MIGRACAO.md)

O roteiro PDF do professor foi examinado e suas exigências foram resumidas nesta documentação. A validação acadêmica do problema local, do público, da ODS/meta e das contribuições do grupo permanece pendente.
