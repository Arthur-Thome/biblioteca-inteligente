# Mapa do código após a refatoração

| Necessidade de alteração | Arquivo principal | Integrações relacionadas |
|---|---|---|
| Iniciar e configurar Flask, sessões e CSRF | `app.py`, `backend/__init__.py` | Chave local, cookies, identidade validada, CSRF, limite de corpo |
| Alterar telas de cadastro/login e logout | `templates/cadastro.html`, `templates/login.html`, `templates/index.html` | `backend/routes.py`, meta e campos CSRF, `static/style.css` |
| Alterar validação da confirmação de senha | `static/auth.js` | Campos `#senha` e `#confirmacao`; o servidor repete a validação em `/cadastro` |
| Validar e persistir usuários | `backend/routes.py`, `backend/repositories/usuarios.py` | Hash Werkzeug, tabela `usuarios`, mensagens públicas |
| Alterar biblioteca por usuário | `backend/routes.py`, `backend/repositories/biblioteca.py`, `backend/repositories/livros.py` | `GET/POST/DELETE /api/library`, UUID da sessão, PostgreSQL |
| Alterar sessões, proteção CSRF ou limite de login | `backend/__init__.py`, `backend/routes.py` | Cookie Flask, token por sessão, rate limit em memória |
| Criar ou alterar endpoint | `backend/routes.py` | Validadores, catálogo, OCR e recomendações |
| Ajustar consulta Open Library | `backend/catalogo.py` | `CatalogError`, transformação e cache |
| Alterar busca por título/autor/ISBN ou normalização bibliográfica | `backend/catalogo.py`, `backend/routes.py` | `GET /api/search`, Search API Open Library, IDs de obra/edição |
| Alterar integração Google Books opcional | `backend/providers/google_books.py` | `GOOGLE_BOOKS_API_KEY` local; complemento somente por ISBN exato |
| Alterar campos bibliográficos exibidos nos resultados | `backend/catalogo.py`, `static/app.js`, `static/style.css`, `templates/index.html` | `#search-type`, cards `.book-item`, `textContent`, CSS dos metadados |
| Alterar persistência de metadados complementares | `backend/models.py`, `backend/repositories/livros.py`, `backend/routes.py`, `migrations/versions/2026_11_20_9a7d31f2c4e8_metadados_catalogo.py` | coluna JSONB `livros.metadados`, migração Alembic aditiva |
| Alterar processamento, ordem das detecções, consultas OCR e pontuação | `backend/visao_computacional.py` | Pillow, NumPy, RapidOCR, RapidFuzz; limiar heurístico atual de 50 pontos; ver `docs/VISAO_COMPUTACIONAL.md` |
| Avaliar OCR reproduzivelmente em capas locais | `scripts/avaliar_ocr.py`, `tests/fixtures/ocr/manifest.json` | Modelos locais `models_ocr/`; Open Library opcional; resultados em `docs/AVALIACAO_OCR.md` |
| Ajustar seleção de recomendações | `backend/recomendacoes.py` | validação e pesquisa por assunto |
| Validar uploads ou JSON recebido | `backend/validacoes.py` | rotas Flask e formato de livro |
| Alterar textos/estrutura/IDs da tela | `templates/index.html` | IDs consumidos por `static/app.js` |
| Alterar cores, dimensão, espaçamento e breakpoints | `static/style.css` | Classes de autenticação, biblioteca, upload e elementos criados no JS |
| Alterar câmera, chamadas HTTP ou desenho dos cards | `static/app.js` | CSRF, `/api/library`, `/api/recognize`, `/api/search`, `/api/recommend` |
| Executar ou ampliar testes | `tests/test_app.py` | Flask test client, mocks de OCR e catálogo |
| Atualizar instruções para execução | `README.md`, `INICIAR_WINDOWS.bat` | dependências declaradas em `requirements.txt` |
| Preparar o ambiente e o cluster local | `scripts/instalar_ambiente.ps1` | .venv, modelos OCR, .env restrito e PostgreSQL 17 |
| Iniciar, encerrar e verificar serviços locais | `INICIAR.bat`, `PARAR.bat`, `VERIFICAR.bat`, `scripts/*.ps1` | Flask, cluster marcado do projeto, portas locais |
| Criar/verificar bancos e ajustar privilégios | `scripts/configurar_postgres.py` | Psycopg, PostgreSQL em loopback; DDL reservado à administração |
| Configurar engine, URL e transações | `backend/database.py` | `.env`, SQLAlchemy, Psycopg; destino restrito ao principal ou `_test` |
| Alterar entidades e restrições | `backend/models.py` | UUID, JSONB, timestamps, chaves e índices PostgreSQL |
| Criar ou consultar contas | `backend/repositories/usuarios.py` | Sessão SQLAlchemy; username canônico e hash recebido |
| Manter catálogo bibliográfico | `backend/repositories/livros.py` | UUID, ISBN e origem/ID de edição; título não é único |
| Consultar biblioteca por proprietário | `backend/repositories/biblioteca.py` | Sempre exige `usuario_id`; exclusão mantém livro compartilhado |
| Manter progresso pessoal | `backend/repositories/progresso.py` | Associação com dono e limites de páginas |
| Manter metas de leitura | `backend/repositories/metas.py` | Filtro obrigatório de proprietário e período validado |
| Manter preferências | `backend/repositories/preferencias.py` | Categoria, normalização e nível por usuário |
| Criar e aplicar migrações | `alembic.ini`, `migrations/` | Admin aplica DDL; executar primeiro na base `_test` |
| Executar testes PostgreSQL reais | `tests/test_database.py` | Exclusivamente `biblioteca_inteligente_test` |
| Testar persistência após reinício | `scripts/testar_persistencia_postgres.py` | Marcador descartável restrito ao banco `_test` |
| Verificar revisão de migração e endpoint de saúde | `scripts/verificar_migracoes.py`, `scripts/verificar_flask.py` | Verificações locais sem imprimir erros/credenciais internos |
| Criar backup local | `scripts/backup_postgres.ps1` | pg_dump, `postgres/backups/` |
| Revisar arquitetura e contratos | `docs/ARQUITETURA.md`, `docs/INTEGRACAO_FRONTEND_BACKEND.md` | fluxo atual e endpoints |

## Gerenciamento pessoal — Etapa 8

| Alteração | Arquivo | Responsabilidade |
|---|---|---|
| Campos pessoais da associação | `backend/models.py`; `migrations/versions/2026_11_20_c4e8a19f07d2_gerenciamento_biblioteca.py` | Favorito, observação, limite e índice por conta |
| Pesquisa, filtros, ordenação e página | `backend/repositories/biblioteca.py` | SQLAlchemy parametrizado e escopo de proprietário |
| Contratos HTTP da biblioteca | `backend/routes.py` | GET paginado, detalhes GET, atualização PATCH e remoção DELETE |
| Controles da coleção e diálogo | `templates/index.html` | Pesquisa pessoal, filtros, lista, controles e detalhes |
| Eventos e chamadas à API | `static/app.js` | Atualização da coleção, favoritos, notas, detalhes e paginação |
| Aparência e responsividade | `static/style.css` | Filtros, cards, favorito, diálogo e telas estreitas |
| Teste visual autenticado | `scripts/verificar_ui_etapa8.py` | Fluxo isolado em `_test` e captura de notebook/celular |
| Regras e contratos completos | `docs/BIBLIOTECA_PESSOAL.md`, `docs/GERENCIAMENTO_LIVROS.md` | Escopo, segurança e endpoints |

## ODS, progresso e metas — Etapa 9

| Funcionalidade | Arquivos principais | Responsabilidade |
|---|---|---|
| Página pública ODS | `backend/routes.py` (`sobre_ods`), `templates/sobre_ods.html`, `static/style.css` | ODS 4, meta 4.6, limitações e quatro perguntas acadêmicas |
| Progresso de leitura | `backend/routes.py` (`library_progress_get`, `library_progress_put`), `backend/repositories/progresso.py`, `backend/models.py` | Status, páginas, datas e percentual em `progresso_leitura` |
| Metas | `backend/routes.py` (`goals_*`), `backend/repositories/metas.py`, `metas_leitura` | CRUD por proprietário e contagem no período |
| Preferências | `backend/routes.py` (`preferences_*`), `backend/repositories/preferencias.py`, `preferencias` | Interesses privados para recomendações |
| Recomendações | `backend/recomendacoes.py`, `backend/catalogo.py` | Favorece assunto/favoritos/interesses, filtra títulos próprios e explica sugestões |
| Interface | `templates/index.html`, `static/app.js`, `static/style.css` | Formulários, JSON/CSRF, estados e indicadores responsivos |
| Documentação acadêmica | `docs/ODS_E_JUSTIFICATIVA.md`, `docs/PROGRESSO_LEITURA.md`, `docs/METAS_LEITURA.md`, `docs/RECOMENDACOES.md` | Fontes, contratos, regras e limitações |

As bibliotecas novas são persistidas no PostgreSQL e filtradas pela sessão autenticada. O frontend somente detecta a existência de `estante-livros-v1` para apresentar o aviso de legado; não lê, modifica ou importa os registros antigos. Importação futura continua pendente e deverá seguir [PLANO_MIGRACAO_LOCALSTORAGE.md](PLANO_MIGRACAO_LOCALSTORAGE.md). Progresso, metas e preferências possuem interface integrada e permanecem vinculados ao proprietário autenticado.
