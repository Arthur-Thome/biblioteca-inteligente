# Integração frontend/backend — Etapas 5 e 7

O sistema atende em `127.0.0.1:5000`. Os formulários HTML enviam POST ao Flask com `csrf_token`; `static/app.js` lê o token da meta tag e inclui `X-CSRFToken` em requisições que alteram estado. O Flask valida a conta pela sessão assinada e PostgreSQL antes de uma página ou API privada executar.

## Cadastro e login

- **HTML:** `templates/cadastro.html` contém `#nome`, `#nome_usuario`, `#senha`, `#confirmacao` e token oculto; `templates/login.html` contém `#nome_usuario`, `#senha` e token oculto. Os estilos ficam em `static/style.css` nas classes `.auth-card`, `.auth-form` e `.auth-message`.
- **JavaScript:** `static/auth.js` compara senha e confirmação nos eventos `input` e `submit`; as demais regras nativas usam `required`, `minlength` e `maxlength`. Nenhum script armazena credenciais.
- **Backend:** `POST /cadastro` executa `backend.routes.cadastrar`, valida os campos, calcula hash Werkzeug e chama `repositories.usuarios.criar_usuario`; `POST /login` chama `obter_usuario_por_nome`, valida com `check_password_hash` e cria sessão mínima.
- **Resposta:** cadastro válido redireciona para login; login válido redireciona para `/`. Erros retornam página com mensagens genéricas ou de validação.

## Página da biblioteca

- **HTML:** `templates/index.html` oferece `#image-input`, `#open-camera-btn`, `#capture-btn`, `#recognize-btn`, `#search-input`, `#search-btn`, `#search-results`, `#library-books`, `#recommend-btn`, `#recommend-results`, `#legacy-notice` e formulário POST de logout. Classes de apresentação ficam em `static/style.css`.
- **Autorização:** `backend.__init__.load_authenticated_user` valida `session.usuario_id` em `usuarios` e disponibiliza a conta como `g.usuario`. `GET /` redireciona ao login se não existir conta válida.
- **Legado:** o script apenas verifica se `localStorage` contém a chave `estante-livros-v1` para mostrar a nota; ele não lê JSON, não altera o armazenamento e não envia esse conteúdo ao servidor.

## Envio de imagem e câmera

- **Arquivo e elementos:** `templates/index.html` usa `#image-input`, `#image-preview`, `#recognize-btn` e `#scan-status`; `static/style.css` organiza `.dropzone`, `.preview`, `.camera-stage` e `.camera-actions`.
- **JavaScript:** `static/app.js` valida tipo/tamanho localmente; a webcam abre por `getUserMedia`, captura um quadro em canvas e converte em JPEG. O evento de análise envia `FormData` com o campo `image` por POST `/api/recognize`, incluindo CSRF.
- **Python:** `backend.routes.recognize` valida multipart e bytes, chama `validate_image_bytes`, `get_ocr_engine`, `extract_cover_text` e a pesquisa Open Library para candidatos.
- **Resposta e DOM:** JSON inclui `detected`, `books`, `queries` e `message`; o script atualiza `#ocr-text`, `#search-results` e `#scan-status`. Falha de OCR retorna erro genérico, enquanto falha de catálogo preserva o texto extraído.

Na Etapa 6, `extract_cover_text` corrige EXIF, limita a imagem a 1700 × 1700, aplica o contraste existente e ordena caixas válidas do RapidOCR de cima para baixo. `suggest_search_queries` prioriza linhas e combinações adjacentes pela confiança de OCR; `score_ocr_match` pontua título e pode aplicar reforço limitado por palavras do autor. `static/app.js` preserva os contratos da rota, permite busca manual e apresenta candidatos para confirmação. A implementação e limites da avaliação estão descritos em [VISAO_COMPUTACIONAL.md](VISAO_COMPUTACIONAL.md) e [AVALIACAO_OCR.md](AVALIACAO_OCR.md).

## Pesquisa bibliográfica

- **Elementos:** `#search-input`, `#search-btn`, `#search-results` e `#scan-status`; cards usam `.book-item`, `.book-cover`, `.book-meta` e `.book-add`.
- **JavaScript:** `#search-type` escolhe título, autor ou ISBN; clique ou Enter chama `searchManually`, que envia GET `/api/search?q=...&type=...`.
- **Python/serviço:** `backend.routes.search` valida consulta e tipo e chama `backend.catalogo.search_books`. O adaptador Open Library consulta `/search.json`; quando a chave opcional está configurada, `backend.providers.google_books` tenta complementar campos vazios exclusivamente após ISBN exato. O cache tem capacidade 256 e validade de uma hora.
- **Tolerância a erros de OCR:** buscas por título repetem a consulta com o campo geral `q` apenas quando nenhum título da resposta estrita alcança similaridade RapidFuzz 90. Os resultados de ambas as respostas são unidos apenas pelo identificador canônico da obra e, nesse fallback, são reordenados pela similaridade do título. Se a consulta ampla falhar, os resultados estritos permanecem disponíveis.
- **Resposta:** JSON `books` conserva ID de obra, título e contrato anterior, com metadados adicionais disponíveis e proveniência. `static/app.js` cria cards usando elementos DOM e `textContent`, exibindo subtítulo, editora, ano, páginas, ISBN e descrição quando presentes. Consulta curta ou tipo inválido retorna 400; falha do catálogo retorna 503. Google Books ausente não interrompe Open Library.

## Confirmação e persistência de metadados

O botão do card chama `addBook` e envia `catalog_id`, título, autor, ano, assuntos, capa validada e o subconjunto permitido de metadados a `POST /api/library`, incluindo CSRF. `backend.routes.library_add` rejeita campos inesperados, tipos inválidos e proveniência desconhecida. `repositories.livros.criar_livro` salva os campos consolidados existentes e o objeto complementar em `livros.metadados` JSONB. A associação pessoal continua sendo criada por `adicionar_livro` com UUID da conta validada pela sessão. Não há gravação automática por ordenação ou pontuação.

## Adição, consulta e remoção da biblioteca

- **Consulta:** `loadLibrary` envia GET `/api/library`; a rota chama `listar_livros_usuario` com `g.usuario.id`, carrega metadados da conta e responde `{"books": [...]}`. `renderLibrary` atualiza `#library-books`, `#book-count` e `#empty-library`.
- **Adição:** `addBook` envia JSON por POST `/api/library` com `catalog_id`, título, autor, ano, assuntos e capa. A rota valida os campos, busca/cria o registro por catálogo com `obter_por_catalogo`/`criar_livro`, chama `adicionar_livro` e responde com ID da associação. O servidor ignora qualquer `usuario_id` enviado pelo navegador.
- **Remoção:** botão `.remove-btn` envia DELETE `/api/library/<id da associação>`; `remover_livro_usuario` filtra UUID e proprietário. O registro bibliográfico compartilhado permanece no banco. HTTP 404 representa associação inexistente ou alheia.
- **Estado:** a página atualiza cards após GET. Erros de rede ou respostas inesperadas aparecem em `#scan-status`; HTTP 401 redireciona ao login.

## Recomendações

`#recommend-btn` envia POST `/api/recommend` com token CSRF e sem lista de livros do navegador. A rota consulta a biblioteca da sessão no PostgreSQL, valida a coleção e chama `recommend_books`, que pesquisa assuntos na Open Library. JSON contém `books`, `subjects` e mensagem opcional; `renderRecommendations` atualiza `#recommend-results` e `#recommend-status`. Bibliotecas vazias retornam lista vazia; falha de catálogo retorna 503.

## Rotas públicas e proteção

## Página pública ODS 4

`GET /sobre-ods` renderiza `templates/sobre_ods.html` sem login, banco ou API externa. A página usa as classes `.ods-hero`, `.ods-card`, `.ods-questions` e `.ods-emphasis` em `static/style.css`. O menu principal e as telas de autenticação encaminham para a rota. A tela apresenta ODS 4, relação proposta à meta 4.6, as quatro perguntas do professor, funcionamento, limites e referências. Nenhum dado acadêmico é enviado ao backend.

## Progresso de leitura

O diálogo `#book-details-dialog` em `templates/index.html` inclui `#progress-status`, `#progress-pages-read`, `#progress-total-pages`, `#progress-started` e `#progress-completed`. `static/app.js` recebe o objeto `progress` junto da listagem/detalhes e envia PUT JSON com token CSRF a `/api/library/<UUID>/progress`. `backend.routes.library_progress_put` valida campos e datas, deriva o proprietário de `g.usuario` e chama `salvar_progresso`; GET usa `obter_progresso`. O repositório confere a associação própria e a tabela `progresso_leitura` persiste estado, páginas e datas. A resposta inclui percentual calculado ou `null` quando não há total conhecido. O cliente atualiza o status e recarrega cards/metas.

## Metas de leitura

`#goal-form` envia objetivo e datas ISO para POST `/api/goals`; edição usa PUT `/api/goals/<UUID>`, listagem usa GET `/api/goals` e remoção usa DELETE. `static/app.js` renderiza barra, contagem e ações; CSS usa `.goal-form`, `.goal-card` e `.goal-progress-fill`. As rotas Flask validam JSON, CSRF e sessão e chamam `backend.repositories.metas`. A camada consulta `metas_leitura` e `contar_livros_concluidos`, que agrega conclusões de `progresso_leitura` pelo proprietário e intervalo. A resposta contém concluídos, restantes e percentual; nenhum `usuario_id` é aceito do navegador.

## Preferências e recomendações

`#preference-form` usa POST `/api/preferences`; listagem e remoção usam GET e DELETE. `static/app.js` atualiza `#preferences-list` com texto seguro. POST `/api/recommend` consulta livros, favoritos e preferências da conta autenticada no PostgreSQL. `backend.recomendacoes.recommend_books` monta consultas com assuntos recorrentes, favoritos e interesses por nível e chama `backend.catalogo.search_books`, que acessa Open Library. A resposta contém sugestões, motivos e assuntos consultados; IDs e títulos próprios são excluídos. A pontuação heurística não é uma probabilidade.

`GET /api/health` continua público e informa somente nomes dos componentes. Cadastro, login e logout usam token CSRF; POST, PUT, PATCH e DELETE das APIs também são verificados. A sessão tem cookie HttpOnly/SameSite=Lax e permanece compatível com HTTP local; hospedagem HTTPS exigirá cookie Secure.

## Biblioteca pessoal — Etapa 8

Na seção `#library-section`, `templates/index.html` fornece `#library-query`, `#library-author`, `#library-subject`, `#favorites-only`, `#library-sort` e os controles de página. `static/style.css` estiliza os campos, cards, estados de favorito e diálogo de detalhes. `static/app.js` escuta mudanças nos campos, aplica atraso curto à digitação e envia `GET /api/library` com pesquisa, filtros, ordenação e página. A rota valida os parâmetros e chama `listar_pagina_usuario`; o repositório SQLAlchemy restringe a consulta ao ID de sessão e devolve dados da página, contagens e filtros. A consulta não chama serviços externos.

O botão de detalhes chama `GET /api/library/<uuid>`. A rota chama o repositório proprietário, serializa campos bibliográficos e pessoais e responde 404 para associações que não pertençam à conta. O JavaScript preenche `#book-details-dialog` com nós de texto/`textContent`, sem interpretar observações como HTML. Favorito e observação são atualizados por `PATCH /api/library/<uuid>` com token CSRF; o repositório altera somente a associação do proprietário. A remoção usa `DELETE /api/library/<uuid>`, confirmação no navegador e mantém o registro bibliográfico compartilhado.

O JSON de listagem contém `books`, `pagination`, `summary` e `filters`; cada livro contém os campos bibliográficos disponíveis e `favorite`, `notes`, `added_at` e `updated_at`. As mutações devolvem o objeto atualizado. Falhas de autenticação, CSRF, validação ou propriedade retornam erros HTTP controlados, apresentados pela interface em uma região de status. As regras constam em `docs/BIBLIOTECA_PESSOAL.md` e `docs/GERENCIAMENTO_LIVROS.md`.
