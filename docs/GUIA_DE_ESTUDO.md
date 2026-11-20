# Guia de estudo do código

Este guia acompanha o código existente da Biblioteca Inteligente e explica o caminho dos dados entre navegador, Flask, visão computacional, catálogo e PostgreSQL. A leitura não substitui a execução do projeto nem a confirmação dos fluxos durante a apresentação.

## 1. Inicialização do Flask

`INICIAR.bat` encaminha a execução para `scripts/iniciar.ps1`. O script verifica a configuração local, inicia o cluster PostgreSQL do projeto quando necessário, ativa `.venv` e inicia `scripts/executar_flask.py`. O ponto de entrada `app.py` importa a fábrica `create_app` de `backend/__init__.py`; a fábrica configura sessões, CSRF, limites de upload, conexão com banco e o Blueprint de `backend/routes.py`. A aplicação local responde em `http://127.0.0.1:5000`.

## 2. Como HTML chega ao navegador

As rotas Flask renderizam templates Jinja em `templates/`. A página pública `/sobre-ods` usa `templates/sobre_ods.html`; a interface autenticada usa `templates/index.html`; cadastro e login usam `templates/cadastro.html` e `templates/login.html`. Os templates incluem arquivos estáticos por meio do mecanismo Flask, sem inserir caminhos absolutos da máquina.

## 3. Como CSS altera a interface

`static/style.css` define cores, tipografia, dimensões, alinhamento, espaçamentos, estados de interação e regras responsivas. A classe ou o ID identificado no template permite localizar a regra correspondente. A página ODS utiliza classes como `.ods-hero`, `.ods-card`, `.ods-questions` e `.ods-emphasis`; os componentes da biblioteca e de progresso possuem seletores próprios documentados em `docs/INTEGRACAO_FRONTEND_BACKEND.md`.

## 4. Como JavaScript recebe eventos

`static/app.js` localiza elementos da página por IDs e registra eventos de clique, envio de formulário e alteração de campos. `static/auth.js` trata a confirmação de senha no cadastro. As funções JavaScript modificam a interface usando elementos DOM e texto seguro; o código evita interpretar observações pessoais como HTML.

## 5. Como JavaScript envia requisições

As funções de `static/app.js` enviam `fetch` às rotas JSON de `backend/routes.py`. Leitura de dados usa GET; inclusão usa POST; atualização usa PUT ou PATCH; remoção usa DELETE. Ações que alteram dados incluem token CSRF. Upload de capa utiliza multipart/form-data e o campo `image`; chamadas JSON declaram o tipo de conteúdo e enviam os campos aceitos pela rota.

## 6. Como Flask recebe e responde

`backend/routes.py` valida parâmetros, sessão, token CSRF, proprietário, formato e conteúdo das requisições. Os endpoints devolvem JSON com dados da operação ou erro HTTP controlado. A interface apresenta carregamento, resultado e falha em regiões de status; HTTP 401 ou sessão encerrada direciona ao login.

## 7. Como a imagem chega ao RapidOCR

O formulário ou câmera da página em `templates/index.html` chama a rotina de reconhecimento em `static/app.js`. O navegador envia o arquivo à rota autenticada `POST /api/recognize`. `backend/routes.py` valida o upload e chama `backend.visao_computacional.extract_cover_text`; `backend/validacoes.py` contém a validação de bytes e tipo. O processamento usa Pillow/NumPy e o motor RapidOCR inicializado e reutilizado por `get_ocr_engine`, com modelos locais em `models_ocr/`. Imagens não são persistidas como parte do fluxo de reconhecimento.

## 8. Como o OCR reconhece texto

`backend/visao_computacional.py` corrige a orientação EXIF, limita dimensões, prepara a imagem e organiza caixas de texto por posição e confiança. `suggest_search_queries` constrói trechos de consulta, e `score_ocr_match` compara texto reconhecido a títulos e autores sem tratar a pontuação heurística como probabilidade. A rota retorna textos e candidatos; quando não há texto legível, a interface recebe orientação para aproximar a capa ou pesquisar manualmente.

## 9. Como o catálogo identifica candidatos

`backend/catalogo.py` consulta a Open Library, transforma campos bibliográficos e normaliza a resposta. `backend/routes.py` usa as consultas derivadas do OCR e devolve candidatos para confirmação humana. `backend/providers/google_books.py` é complementar e opcional; seu uso depende de configuração local e, quando ativo, exige ISBN coincidente para complementar metadados. A busca real depende de internet.

## 10. Como PostgreSQL armazena dados

`backend/database.py` prepara engines e sessões SQLAlchemy a partir da configuração local. `backend/models.py` define `Usuario`, `Livro`, `BibliotecaUsuario`, `ProgressoLeitura`, `MetaLeitura` e `Preferencia`. `backend/repositories/` concentra consultas e transações; `migrations/versions/` registra as alterações de esquema Alembic. O banco armazena contas, livros, associações pessoais, estado de leitura, metas e preferências. O código não migra automaticamente a antiga chave `estante-livros-v1` do navegador.

## 11. Como login e sessão funcionam

Cadastro, login e logout são rotas em `backend/routes.py`. `backend/repositories/usuarios.py` consulta e grava contas; senhas ficam armazenadas com hash seguro. A sessão Flask assinada mantém a identidade validada para cada requisição. O proprietário nunca é escolhido por um UUID livre enviado pelo navegador. Rotas privadas exigem autenticação, e operações de escrita verificam CSRF. `docs/AUTENTICACAO.md` e `docs/SESSOES_E_SEGURANCA.md` descrevem os detalhes.

## 12. Como recomendações são geradas

O botão de recomendações chama `POST /api/recommend`. A rota obtém da conta autenticada livros, favoritos e preferências no PostgreSQL. `backend/recomendacoes.py` seleciona assuntos e interesses para consultar `backend.catalogo.search_books`, filtra obras já pertencentes à biblioteca, remove duplicações e acrescenta justificativas legíveis. O algoritmo é heurístico, depende da Open Library e não apresenta pontuação como chance estatística de acerto.

## 13. Como progresso e metas são calculados

O diálogo de detalhes em `templates/index.html` envia status, páginas e datas a `PUT /api/library/<UUID>/progress`. A rota valida os valores e chama `backend/repositories/progresso.py`; percentual é calculado somente quando há total de páginas conhecido. `POST`, `GET`, `PUT` e `DELETE /api/goals` gerenciam metas próprias. `backend/repositories/metas.py` conta associações distintas concluídas no intervalo inclusivo da meta. A interface apresenta quantidade, restante e barra percentual; o percentual não é confiança do OCR.

## 14. Como a ODS 4 se relaciona ao programa

`templates/sobre_ods.html` e `docs/ODS_E_JUSTIFICATIVA.md` descrevem a relação proposta com a ODS 4 e a meta 4.6 como indireta, por facilitar tarefas associadas à organização e descoberta de leituras. O sistema não oferece alfabetização ou ensino de matemática e não mede impacto educacional. Evidências locais, adequação acadêmica definitiva da meta e contribuições dos integrantes continuam pendentes.

## Roteiro de leitura técnica

1. A leitura começa por `app.py` e `backend/__init__.py` para acompanhar a inicialização.
2. `backend/routes.py` mostra a fronteira HTTP entre navegador e serviços.
3. `backend/visao_computacional.py` explica o processamento OCR.
4. `backend/catalogo.py` e `backend/recomendacoes.py` mostram busca e seleção de candidatos.
5. `backend/models.py`, `backend/database.py` e `backend/repositories/` apresentam persistência e isolamento.
6. `templates/index.html`, `static/app.js` e `static/style.css` mostram a interface e sua integração.
7. `docs/TESTES.md` e `tests/` distinguem verificações automatizadas de limitações ainda não homologadas.
