# Arquitetura implementada

## Catálogo e metadados da Etapa 7

`backend/catalogo.py` preserva a interface de serviço consumida pelo OCR, recomendações e busca manual. O módulo normaliza respostas Open Library, limita o cache a 256 consultas por janelas de uma hora e complementa somente campos ausentes a partir do Google Books quando há ISBN normalizado coincidente. Em buscas por título, uma segunda consulta ampla é realizada somente se nenhum resultado estrito atingir similaridade 90; os candidatos são então deduplicados por ID de obra e reordenados por proximidade textual. `backend/providers/google_books.py` implementa a integração opcional, desativada sem chave em `.env` ou no ambiente. `backend/providers/` mantém adaptadores externos separados.

O modelo `Livro` contém agora `metadados` JSONB para valores complementares e sua proveniência. A revisão aditiva `9a7d31f2c4e8` não altera registros existentes. A biblioteca pessoal continua ligada a IDs internos e à conta autenticada; pesquisa externa não grava livros até confirmação explícita.

## Visão geral

A Etapa 5 acrescenta autenticação Flask e uso dos repositórios PostgreSQL para contas e livros por usuário. A aplicação permanece local; OCR, consulta bibliográfica e recomendação por assunto continuam disponíveis após autenticação.

```text
app.py
  -> backend.create_app
      -> backend.routes (Blueprint Flask)
          -> backend.validacoes
          -> backend.visao_computacional
          -> backend.catalogo -> Open Library; Google Books complementar opcional
          -> backend.recomendacoes -> backend.catalogo
  -> templates/index.html
      -> static/style.css
      -> static/app.js -> APIs Flask
      -> sessão Flask assinada (UUID validado no PostgreSQL)
      -> /api/library -> repositories -> PostgreSQL

Camada de dados:
backend.routes -> backend.repositories -> backend.database -> SQLAlchemy/Psycopg -> PostgreSQL 17
                      migrations/ -> Alembic (credencial administrativa)
```

## Módulos

- `app.py`: ponto de entrada e execução local em `127.0.0.1:5000`, com modo debug desativado.
- `backend/__init__.py`: fábrica Flask, chave local persistente, duração e atributos da sessão, validação de conta e verificação CSRF.
- `backend/routes.py`: cadastro, login, logout, autorização das rotas, biblioteca por sessão, contratos OCR/busca/recomendação e respostas de erro.
- `backend/catalogo.py`: normalização, validação de identificador, transformação de documentos, sessão HTTP, limite de frequência, cache com validade e integração primária Open Library.
- `backend/providers/google_books.py`: consulta opcional ao endpoint público de volumes, validação de dados e complementação apenas por ISBN exato.
- `backend/visao_computacional.py`: inicialização tardia e reutilizada do RapidOCR, preparação Pillow/NumPy, extração e ordenação espacial de caixas, consultas priorizadas pela confiança e pontuação heurística RapidFuzz. O parâmetro `Global.model_root_dir` aponta para `models_ocr/` dentro do projeto.
- `backend/recomendacoes.py`: filtro de assuntos genéricos e classificação de candidatos consultados no catálogo.
- `backend/validacoes.py`: verificação de uploads e normalização defensiva da lista JSON recebida para recomendação.
- `backend/database.py`: leitura restrita do `.env`, URL SQLAlchemy validada para banco principal/teste, criação do engine e contexto transacional com rollback e fechamento.
- `backend/models.py`: modelos UUID para usuários, livros, biblioteca, progresso, metas e preferências, com chaves, índices, timestamps e restrições.
- `backend/repositories/`: consultas e gravações transacionais. As rotas de biblioteca fornecem o UUID obtido pela sessão validada e os repositórios filtram associações pelo proprietário.
- `static/auth.js`: valida localmente a correspondência de senha e confirmação; o backend repete a validação obrigatória.
- `migrations/` e `alembic.ini`: revisões versionadas; a conta administrativa aplica DDL e privilégios padrão liberam DML à role runtime.
- `templates/login.html`, `templates/cadastro.html`, `templates/index.html`, `static/style.css`, `static/app.js`: formulários, token CSRF, interface autenticada, chamadas HTTP e renderização por conta.

## Gerenciamento pessoal da biblioteca — Etapa 8

`backend/repositories/biblioteca.py` concentra consulta paginada e alteração dos dados pessoais da associação. `backend/routes.py` expõe listagem autenticada, detalhes, PATCH para favorito/observação e remoção. O modelo mantém metadados bibliográficos em `livros` e preferências pessoais em `biblioteca_usuario`, pela migração aditiva `c4e8a19f07d2`. `templates/index.html`, `static/app.js` e `static/style.css` compõem a interface de pesquisa, filtros, ordenação, paginação, favoritos e detalhes. Os critérios SQL ficam limitados ao proprietário autenticado; detalhes e mutações usam o ID da associação e falham para outra conta. `docs/BIBLIOTECA_PESSOAL.md` descreve o fluxo e os campos.

## Limites e dependências externas

Open Library permanece necessária para pesquisa e recomendações online. RapidOCR e ONNX Runtime executam o reconhecimento localmente, com modelos carregados quando a funcionalidade de OCR é solicitada. O CSS referencia fontes do Google Fonts, e capas fornecidas pelo catálogo podem depender da internet. O estado de saúde não verifica conectividade nem carrega os modelos.

Os bancos local principal e de teste permanecem na instância `127.0.0.1:5433`; a revisão local atual é `d1a45f8c2e70`. A migração de origem da obra é aditiva e conserva registros existentes. Novos cadastros, livros e dados pessoais entram no PostgreSQL. A chave legada `estante-livros-v1` não é lida nem alterada; a interface avisa que não houve importação.

## Ambientes local e Vercel

O ambiente Windows usa `.env`, PostgreSQL portátil e `static/`. Com `VERCEL=1`, a fábrica exige `DATABASE_URL` remoto com TLS, chave de sessão persistente e `DATABASE_URL_ADMIN` somente para execução de migrações; o runtime não usa o endereço local. Os engines serverless são compartilhados no processo com pool pequeno. `scripts/build_vercel.py` copia os ativos para `public/static/` durante o build e o Flask local continua servindo `static/`. A configuração e o estado de implantação estão documentados em `docs/DEPLOY_VERCEL.md` e `docs/POSTGRESQL_NEON.md`.

## Origem dos livros e apresentação

`biblioteca_usuario.origem_obra` classifica a obra por conta, com CHECK e índice da revisão `d1a45f8c2e70`. O navegador envia o filtro com os demais critérios de `GET /api/library`; o repositório mantém o escopo do proprietário. `static/formatters.js` converte timestamps ISO em exibição brasileira no fuso `America/Sao_Paulo` e mapeia somente códigos bibliográficos conhecidos. A data armazenada continua inalterada.

## Ambiente local preparado na Etapa 3

- `postgres/runtime/bin` contém a distribuição ZIP PostgreSQL 17.12 da EDB sem serviço Windows instalado.
- `postgres/data` contém o cluster exclusivo do projeto; `postgres/logs` recebe logs e `postgres/backups` recebe dumps.
- `.env` guarda senhas locais com ACL restrita e está ignorado pelo Git; `.env.example` apresenta apenas campos vazios.
- A conta `biblioteca_app` não tem superuser, CREATEDB, CREATEROLE nem permissão de CREATE no schema; recebe DML nas tabelas. Alembic usa a conta administrativa.
- O Flask usa PostgreSQL para contas e livros por usuário, além de consultar Open Library para busca e recomendação. SQLAlchemy, Alembic e Psycopg estão no `.venv`; as rotas chamam repositórios com escopo de proprietário.
- A instalação PostgreSQL 18 preexistente permanece independente e não foi alterada.

## Avaliação OCR da Etapa 6

O conjunto local e reproduzível fica em `tests/fixtures/ocr/`; `scripts/avaliar_ocr.py` mede inferência local e, quando solicitado sem `--sem-catalogo`, consulta a Open Library. O tamanho do conjunto, os resultados medidos, a variante de pré-processamento e as limitações estão em `docs/AVALIACAO_OCR.md`. A amostra disponível é uma capa e não sustenta estimativa geral de precisão.


## Verificação prática de conclusão da Etapa 2

## Funcionalidades finais — Etapa 9

`templates/sobre_ods.html` publica a explicação da ODS 4 e as quatro perguntas acadêmicas. `backend/routes.py` acrescenta `/sobre-ods`, APIs de progresso, metas e preferências. Os dados utilizam as entidades já existentes de `backend/models.py`; `backend/repositories/progresso.py`, `metas.py` e `preferencias.py` realizam operações isoladas pelo usuário. O repositório de metas calcula conclusões no intervalo inclusivo. `static/app.js` preenche o diálogo de progresso, atualiza metas e interesses por JSON com CSRF; `static/style.css` organiza formulários e indicadores responsivos. Não foi necessária migração.

O serviço de recomendação prioriza assuntos de livros favoritos e interesses declarados, exclui identificadores e títulos já cadastrados e entrega motivo textual para cada sugestão. A seleção continua heurística e não equivale a probabilidade. O escopo acadêmico e a relação indireta com a meta 4.6 constam em `docs/ODS_E_JUSTIFICATIVA.md`.

O servidor Flask, RapidOCR, Open Library, interface e câmera virtual foram verificados em etapas anteriores. Na Etapa 5, a persistência autenticada e o isolamento por conta foram testados no banco `biblioteca_inteligente_test`. A homologação da webcam física, as evidências locais da ODS 4, a validação da meta 4.6 e o registro das contribuições reais do grupo permanecem pendentes.
