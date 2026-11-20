'use strict';

const STORAGE_KEY = 'estante-livros-v1';
/** Seleciona um elemento da interface pelo seletor CSS fornecido. */
const qs = (selector) => document.querySelector(selector);
const libraryBox = qs('#library-books');
const resultsBox = qs('#search-results');
const recommendationBox = qs('#recommend-results');
let uploadedFile = null;
let previewUrl = null;
let cameraStream = null;
let libraryPageState = {page: 1, pageSize: 12, totalPages: 0, query: '', author: '', subject: '', favorites: false,
  sort: 'adicionados_recentes'};
let currentDetailsId = null;
let librarySearchTimer = null;
let editingGoalId = null;

// A lista ativa vem do PostgreSQL; o armazenamento legado permanece intocado.
let library = [];

/** Atualiza a mensagem de estado e alterna a classe visual de erro no elemento selecionado. */
function setStatus(selector, message, error = false) {
  const element = qs(selector);
  element.textContent = message || '';
  element.classList.toggle('error', error);
}

/**
 * Envia uma requisição HTTP ao Flask, interpreta JSON e converte falhas em erro
 * legível. As chamadas utilizam /api/recognize, /api/search e /api/recommend;
 * respostas não JSON e erros HTTP não são tratados como resultados válidos.
 */
async function apiRequest(path, options = {}) {
  let response;
  const requestOptions = {...options, headers: {...(options.headers || {})}};
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes((requestOptions.method || 'GET').toUpperCase())) {
    requestOptions.headers['X-CSRFToken'] = qs('meta[name="csrf-token"]').content;
  }
  try {
    response = await fetch(path, requestOptions);
  } catch (_) {
    throw new Error('Não consegui conectar ao servidor Python. Verifique se app.py está aberto.');
  }
  const data = await response.json().catch(() => null);
  if (response.status === 401) {
    window.location.assign('/login');
    throw new Error('A sessão expirou. Entre novamente.');
  }
  if (!response.ok) throw new Error(data?.error || `Erro HTTP ${response.status}`);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('O servidor retornou uma resposta em formato inesperado.');
  }
  return data;
}

/** Cria elemento HTML e atribui texto por textContent para impedir interpretação de marcação recebida. */
function make(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

/** Valida a URL de capa do catálogo e cria imagem segura ou marcador sem capa. */
function coverNode(book) {
  if (typeof book.cover === 'string' && /^https:\/\/covers\.openlibrary\.org\/b\/id\/\d+-M\.jpg$/.test(book.cover)) {
    const img = make('img', 'book-cover');
    img.alt = `Capa de ${book.title}`;
    img.loading = 'lazy';
    img.src = book.cover;
    // O evento error substitui capa indisponível por marcador visual sem nova requisição.
    img.onerror = () => img.replaceWith(make('div', 'book-cover no-cover', '▤'));
    return img;
  }
  return make('div', 'book-cover no-cover', '▤');
}

/** Envia o candidato confirmado a POST /api/library; a conta vem da sessão Flask. */
async function addBook(book) {
  try {
    await apiRequest('/api/library', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({catalog_id: book.id, title: book.title, author: book.author,
        year: book.year, subjects: book.subjects, cover: book.cover,
        metadata: Object.fromEntries(['subtitle', 'description', 'publisher', 'language', 'page_count', 'isbn_10', 'isbn_13', 'metadata_sources', 'metadata_scope', 'edition_id', 'edition_source']
          .filter(key => book[key] !== undefined).map(key => [key, book[key]]))})});
    await loadLibrary();
    setStatus('#scan-status', `“${book.title}” foi adicionado à sua biblioteca.`);
  } catch (error) {
    setStatus('#scan-status', error.message, true);
  }
}

/** Monta um card de resultado/recomendação e conecta a ação de inclusão ao livro confirmado. */
function bookItem(book, recommendation = false) {
  const row = make('div', 'book-item');
  row.appendChild(coverNode(book));
  const meta = make('div', 'book-meta');
  meta.appendChild(make('p', 'book-title', book.title));
  meta.appendChild(make('p', 'book-author', book.author || 'Autor desconhecido'));
  if (book.subtitle) meta.appendChild(make('p', 'book-detail', book.subtitle));
  const details = [book.publisher, book.year, book.page_count ? `${book.page_count} páginas` : null,
    book.isbn_13 || book.isbn_10 ? `ISBN ${book.isbn_13 || book.isbn_10}` : null].filter(Boolean);
  if (details.length) meta.appendChild(make('p', 'book-detail', details.join(' · ')));
  if (book.metadata_scope === 'work') meta.appendChild(make('p', 'book-note', 'Dados associados à obra; podem variar por edição.'));
  if (book.metadata_scope === 'work_and_edition') meta.appendChild(make('p', 'book-note', 'Obra Open Library com edição Google Books vinculada por ISBN exato.'));
  if (book.description) meta.appendChild(make('p', 'book-description', book.description));
  const sourceLabels = {openlibrary: 'Open Library', google_books: 'Google Books'};
  const metadataSources = book.metadata_sources && typeof book.metadata_sources === 'object'
    ? [...new Set(Object.values(book.metadata_sources).filter(source => sourceLabels[source]).map(source => sourceLabels[source]))]
    : [];
  if (metadataSources.length) meta.appendChild(make('p', 'book-note', `Metadados: ${metadataSources.join(' · ')}`));
  else if (book.source) meta.appendChild(make('p', 'book-note', `Fonte: ${sourceLabels[book.source] || 'Catálogo bibliográfico'}`));
  if (recommendation && book.reason) meta.appendChild(make('p', 'book-note', book.reason));
  // A pontuação é heurística e serve apenas para ordenar candidatos, sem indicar probabilidade.
  if (!recommendation && typeof book.match === 'number') meta.appendChild(make('p', 'book-note', 'Pontuação heurística: ' + Math.round(book.match) + '/100'));
  row.appendChild(meta);
  const btn = make('button', 'book-add');
  btn.type = 'button';
  btn.dataset.bookId = book.id;
  const alreadyAdded = library.some(item => item.catalog_id === book.id);
  btn.textContent = alreadyAdded ? 'Adicionado ✓' : '+ Adicionar';
  btn.disabled = alreadyAdded;
  // O evento click confirma a inclusão escolhida e preserva a decisão explícita da pessoa usuária.
  btn.addEventListener('click', () => addBook(book));
  row.appendChild(btn);
  return row;
}

let lastSearch = [];
let lastRecommendations = [];
/** Atualiza os botões dos resultados após mudança na coleção local. */
function renderSearchButtons() {
  renderResults(lastSearch);
  if (lastRecommendations.length) renderRecommendations(lastRecommendations);
}
/** Renderiza candidatos do Flask e controla a visibilidade da seção de resultados. */
function renderResults(books) {
  lastSearch = books;
  resultsBox.replaceChildren();
  qs('#results-section').classList.toggle('hidden', books.length === 0);
  books.forEach(book => resultsBox.appendChild(bookItem(book)));
}
/** Renderiza sugestões do Flask na lista lateral de recomendações. */
function renderRecommendations(books) {
  lastRecommendations = books;
  recommendationBox.replaceChildren();
  books.forEach(book => recommendationBox.appendChild(bookItem(book, true)));
}
/** Renderiza um card pessoal e conecta detalhes, favorito e remoção às rotas autenticadas. */
function savedBookCard(book) {
  const card = make('article', 'saved-book');
  card.appendChild(coverNode(book));
  card.appendChild(make('p', 'book-title', book.title));
  card.appendChild(make('p', 'book-author', book.author || 'Autor não informado'));
  const details = [book.year, book.subjects?.[0]].filter(value => value !== null && value !== undefined && value !== '');
  if (details.length) card.appendChild(make('p', 'book-detail', details.join(' · ')));
  const progress = book.progress || {status: 'nao_iniciado', pages_read: 0, total_pages: null, progress_percent: null};
  const statusLabels = {nao_iniciado: 'Não iniciado', lendo: 'Lendo', concluido: 'Concluído', abandonado: 'Abandonado'};
  card.appendChild(make('p', 'reading-status', `Leitura: ${statusLabels[progress.status] || 'Não iniciado'}`));
  if (progress.progress_percent !== null && progress.progress_percent !== undefined) {
    const meter = make('div', 'book-progress');
    meter.setAttribute('role', 'progressbar');
    meter.setAttribute('aria-label', `Progresso de leitura de ${book.title}`);
    meter.setAttribute('aria-valuemin', '0');
    meter.setAttribute('aria-valuemax', '100');
    meter.setAttribute('aria-valuenow', String(progress.progress_percent));
    const fill = make('span', 'book-progress-fill');
    fill.style.width = `${progress.progress_percent}%`;
    meter.appendChild(fill);
    card.appendChild(meter);
  }
  const actions = make('div', 'saved-book-actions');
  const favorite = make('button', 'favorite-toggle', book.favorite ? '★ Favorito' : '☆ Favoritar');
  favorite.type = 'button';
  favorite.setAttribute('aria-pressed', String(Boolean(book.favorite)));
  favorite.setAttribute('aria-label', book.favorite ? `Remover ${book.title} dos favoritos` : `Marcar ${book.title} como favorito`);
  favorite.addEventListener('click', () => updateFavorite(book));
  actions.appendChild(favorite);
  const detailsButton = make('button', 'btn btn-secondary details-button', 'Detalhes');
  detailsButton.type = 'button';
  detailsButton.addEventListener('click', () => openBookDetails(book.id));
  actions.appendChild(detailsButton);
  const remove = make('button', 'remove-btn', 'Remover');
  remove.type = 'button';
  remove.addEventListener('click', () => removeBook(book));
  actions.appendChild(remove);
  card.appendChild(actions);
  return card;
}

/** Desenha a página da coleção e exibe totais calculados no PostgreSQL. */
function renderLibrary(data) {
  libraryBox.replaceChildren();
  const summary = data.summary;
  const pagination = data.pagination;
  qs('#empty-library').classList.toggle('hidden', summary.total_books > 0 || pagination.total > 0);
  qs('#book-count').textContent = `${summary.total_books} ${summary.total_books === 1 ? 'livro' : 'livros'}`;
  qs('#library-summary').textContent = `${summary.total_books} livros · ${summary.total_favorites} favoritos · ${pagination.total} nesta consulta`;
  qs('#recommend-btn').disabled = summary.total_books === 0;
  library.forEach(book => libraryBox.appendChild(savedBookCard(book)));
  qs('#library-page-label').textContent = `Página ${pagination.page} de ${Math.max(1, pagination.total_pages)}`;
  qs('#library-previous').disabled = pagination.page <= 1;
  qs('#library-next').disabled = pagination.page >= pagination.total_pages;
  qs('#library-pagination').classList.toggle('hidden', pagination.total_pages <= 1);
}

/** Solicita exclusão confirmada da associação pessoal e recarrega uma página válida. */
async function removeBook(book) {
  if (!window.confirm(`Remover “${book.title}” da biblioteca desta conta?`)) return;
  try {
    await apiRequest(`/api/library/${encodeURIComponent(book.id)}`, {method: 'DELETE'});
    setStatus('#library-status', `“${book.title}” foi removido da biblioteca.`);
    recommendationBox.replaceChildren();
    lastRecommendations = [];
    setStatus('#recommend-status', 'Biblioteca alterada. Gere recomendações novamente.');
    const loaded = await loadLibrary();
    if (!loaded && libraryPageState.page > 1) {
      libraryPageState.page -= 1;
      await loadLibrary();
    }
  } catch (error) { setStatus('#library-status', error.message, true); }
}

/** Persiste o favorito no PostgreSQL e atualiza a página retornada pelo backend. */
async function updateFavorite(book) {
  try {
    await apiRequest(`/api/library/${encodeURIComponent(book.id)}`, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({favorite: !book.favorite})
    });
    setStatus('#library-status', book.favorite ? 'Livro removido dos favoritos.' : 'Livro marcado como favorito.');
    await loadLibrary();
  } catch (error) { setStatus('#library-status', error.message, true); }
}

/** Cria um parágrafo textual de metadado sem interpretar conteúdo recebido como HTML. */
function detailLine(label, value) {
  if (value === null || value === undefined || value === '' || (Array.isArray(value) && !value.length)) return null;
  const line = make('p', 'details-line');
  line.appendChild(make('strong', '', `${label}: `));
  line.appendChild(document.createTextNode(Array.isArray(value) ? value.join(', ') : String(value)));
  return line;
}

/** Busca detalhes e dados pessoais por GET /api/library/<id> e abre a caixa acessível. */
async function openBookDetails(itemId) {
  try {
    const data = await apiRequest(`/api/library/${encodeURIComponent(itemId)}`);
    if (!data.book || typeof data.book.title !== 'string') throw new Error('Os detalhes do livro vieram em formato inesperado.');
    const book = data.book;
    currentDetailsId = book.id;
    const content = qs('#details-content');
    content.replaceChildren();
    content.appendChild(coverNode(book));
    content.appendChild(make('h3', 'details-book-title', book.title));
    const fields = [['Subtítulo', book.subtitle], ['Autores', book.authors], ['Ano', book.year],
      ['Gêneros', book.genres], ['Assuntos', book.subjects], ['ISBN', book.isbn_13 || book.isbn_10 || book.isbn],
      ['Editora', book.publisher], ['Idioma', book.language], ['Páginas', book.page_count],
      ['Descrição', book.description], ['Origem', book.source], ['Adicionado à biblioteca', book.added_at],
      ['Última atualização pessoal', book.updated_at]];
    fields.forEach(([label, value]) => {
      const line = detailLine(label, value);
      if (line) content.appendChild(line);
    });
    qs('#details-title').textContent = `Detalhes: ${book.title}`;
    qs('#personal-notes').value = book.notes || '';
    qs('#notes-length').textContent = `${qs('#personal-notes').value.length} / 2.000`;
    qs('#personal-notes').dispatchEvent(new Event('input'));
    const progress = book.progress || {};
    qs('#progress-status').value = progress.status || 'nao_iniciado';
    qs('#progress-pages-read').value = progress.pages_read ?? 0;
    qs('#progress-total-pages').value = progress.total_pages ?? '';
    qs('#progress-started').value = progress.started_at || '';
    qs('#progress-completed').value = progress.completed_at || '';
    qs('#progress-summary').textContent = progress.progress_percent === null || progress.progress_percent === undefined
      ? 'O percentual aparece quando o total de páginas é conhecido.'
      : `${progress.pages_read} de ${progress.total_pages} páginas · ${progress.progress_percent}% concluído.`;
    setStatus('#details-status', '');
    qs('#book-details-dialog').showModal();
  } catch (error) { setStatus('#library-status', error.message, true); }
}

/** Salva status, contagens e datas via PUT /api/library/<id>/progress. */
async function saveReadingProgress() {
  if (!currentDetailsId) return;
  const payload = {
    status: qs('#progress-status').value,
    pages_read: Number(qs('#progress-pages-read').value),
    total_pages: qs('#progress-total-pages').value === '' ? null : Number(qs('#progress-total-pages').value),
    started_at: qs('#progress-started').value || null,
    completed_at: qs('#progress-completed').value || null,
  };
  try {
    const data = await apiRequest(`/api/library/${encodeURIComponent(currentDetailsId)}/progress`, {
      method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    if (!data.progress || typeof data.progress.status !== 'string') {
      throw new Error('A resposta do progresso veio em formato inesperado.');
    }
    qs('#progress-summary').textContent = data.progress.progress_percent === null
      ? 'Progresso salvo. O percentual aparece quando o total de páginas é conhecido.'
      : `${data.progress.pages_read} de ${data.progress.total_pages} páginas · ${data.progress.progress_percent}% concluído.`;
    setStatus('#details-status', 'Progresso salvo nesta conta.');
    await loadLibrary();
    await loadGoals();
  } catch (error) { setStatus('#details-status', error.message, true); }
}

/** Salva observação pessoal por PATCH com texto simples e limite validado no servidor. */
async function savePersonalNotes() {
  if (!currentDetailsId) return;
  const notes = qs('#personal-notes').value;
  try {
    const data = await apiRequest(`/api/library/${encodeURIComponent(currentDetailsId)}`, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({notes})
    });
    if (!data.book || typeof data.book.notes !== 'string' && data.book.notes !== null) {
      throw new Error('A resposta da observação veio em formato inesperado.');
    }
    setStatus('#details-status', 'Observações salvas nesta conta.');
    await loadLibrary();
  } catch (error) { setStatus('#details-status', error.message, true); }
}

/** Serializa filtros locais em parâmetros autorizados e solicita uma única página ao Flask. */
async function loadLibrary() {
  try {
    const params = new URLSearchParams({q: libraryPageState.query, author: libraryPageState.author,
      subject: libraryPageState.subject, favorites: String(libraryPageState.favorites),
      sort: libraryPageState.sort, page: String(libraryPageState.page), page_size: String(libraryPageState.pageSize)});
    const data = await apiRequest(`/api/library?${params.toString()}`);
    if (!Array.isArray(data.books) || !data.pagination || !data.summary) {
      throw new Error('A biblioteca retornou dados em formato inesperado.');
    }
    library = data.books;
    libraryPageState.totalPages = data.pagination.total_pages;
    renderLibrary(data);
    renderSearchButtons();
    setStatus('#library-status', data.pagination.total === 0 && data.summary.total_books > 0
      ? 'Nenhum livro corresponde à pesquisa ou aos filtros.' : '');
    return true;
  } catch (error) {
    setStatus('#library-status', error.message, true);
    return false;
  }
}

/** Aplica filtros combinados a GET /api/library e reinicia a paginação. */
function applyLibraryFilters(debounce = false) {
  libraryPageState.query = qs('#library-query').value.trim();
  libraryPageState.author = qs('#library-author').value.trim();
  libraryPageState.subject = qs('#library-subject').value.trim();
  libraryPageState.favorites = qs('#favorites-only').checked;
  libraryPageState.sort = qs('#library-sort').value;
  libraryPageState.page = 1;
  if (librarySearchTimer) window.clearTimeout(librarySearchTimer);
  if (debounce) librarySearchTimer = window.setTimeout(loadLibrary, 250);
  else loadLibrary();
}

/** Atualiza o contador de caracteres e conserva as observações como texto simples. */
qs('#personal-notes').addEventListener('input', event => {
  qs('#notes-length').textContent = `${event.currentTarget.value.length} / 2.000`;
});
qs('#save-notes').addEventListener('click', savePersonalNotes);
qs('#close-details').addEventListener('click', () => qs('#book-details-dialog').close());
qs('#library-query').addEventListener('input', () => applyLibraryFilters(true));
qs('#library-author').addEventListener('input', () => applyLibraryFilters(true));
qs('#library-subject').addEventListener('input', () => applyLibraryFilters(true));
qs('#favorites-only').addEventListener('change', () => applyLibraryFilters());
qs('#library-sort').addEventListener('change', () => applyLibraryFilters());
qs('#clear-library-filters').addEventListener('click', () => {
  qs('#library-query').value = '';
  qs('#library-author').value = '';
  qs('#library-subject').value = '';
  qs('#favorites-only').checked = false;
  qs('#library-sort').value = 'adicionados_recentes';
  applyLibraryFilters();
});
qs('#library-previous').addEventListener('click', () => {
  if (libraryPageState.page > 1) { libraryPageState.page -= 1; loadLibrary(); }
});
qs('#library-next').addEventListener('click', () => {
  if (libraryPageState.page < libraryPageState.totalPages) { libraryPageState.page += 1; loadLibrary(); }
});

/**
 * Valida tipo e tamanho do arquivo selecionado, cria prévia e habilita OCR.
 * O evento change de #image-input ou a captura da webcam fornece o File;
 * arquivo inválido mantém o fluxo no navegador e apresenta mensagem em #scan-status.
 */
function selectFile(file) {
  if (!file) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    setStatus('#scan-status', 'Escolha um arquivo JPG, PNG ou WEBP.', true);
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    setStatus('#scan-status', 'Arquivo acima de 8 MB. Escolha uma imagem menor.', true);
    return;
  }
  uploadedFile = file;
  qs('#recognize-btn').disabled = false;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  qs('#image-preview').src = previewUrl;
  qs('#image-preview').classList.remove('hidden');
  qs('#camera-icon').classList.add('hidden');
  qs('#upload-label').classList.add('hidden');
  setStatus('#scan-status', `Imagem selecionada: ${file.name}`);
}
// O evento change encaminha o arquivo escolhido pelo controle #image-input.
qs('#image-input').addEventListener('change', event => selectFile(event.target.files?.[0]));

/** Interrompe as faixas de vídeo e oculta a área da webcam sem tocar na biblioteca. */
function stopCamera() {
  if (cameraStream) cameraStream.getTracks().forEach(track => track.stop());
  cameraStream = null;
  qs('#camera-video').srcObject = null;
  qs('#camera-stage').classList.add('hidden');
}
// O evento de clique solicita acesso à câmera e atualiza #camera-video e #camera-stage.
qs('#open-camera-btn').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus('#scan-status', 'Este navegador não oferece acesso à câmera. Envie uma foto do arquivo.', true);
    return;
  }
  stopCamera();
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({video: {facingMode: {ideal: 'environment'}}, audio: false});
    qs('#camera-video').srcObject = cameraStream;
    qs('#camera-stage').classList.remove('hidden');
    setStatus('#scan-status', 'Posicione a capa diante da câmera e clique em Fotografar agora.');
  } catch (_) {
    setStatus('#scan-status', 'Não foi possível acessar a câmera. Conceda permissão ou envie uma imagem.', true);
  }
});
// O botão de fechar encerra todas as faixas concedidas ao fluxo da câmera.
qs('#close-camera-btn').addEventListener('click', stopCamera);
/**
 * Captura um quadro do vídeo, converte-o em JPEG e reutiliza a validação de arquivo.
 * O evento click usa canvas no navegador; falhas de câmera ou conversão aparecem
 * em #scan-status e o OCR só ocorre após o botão de análise.
 */
qs('#capture-btn').addEventListener('click', async () => {
  const video = qs('#camera-video');
  if (!cameraStream || !video.videoWidth) {
    setStatus('#scan-status', 'A câmera ainda está inicializando. Tente novamente.', true);
    return;
  }
  const canvas = document.createElement('canvas');
  const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  if (!blob) {
    setStatus('#scan-status', 'Não foi possível registrar a foto.', true);
    return;
  }
  selectFile(new File([blob], 'capa-da-camera.jpg', {type: 'image/jpeg'}));
  stopCamera();
});

/**
 * Envia o arquivo validado por multipart a POST /api/recognize e apresenta texto,
 * candidatos e mensagens devolvidas pelo Flask. Respostas ausentes ou malformadas
 * geram erro de contrato; o botão retorna ao estado habilitado ao terminar.
 */
qs('#recognize-btn').addEventListener('click', async () => {
  if (!uploadedFile) return;
  const btn = qs('#recognize-btn');
  btn.disabled = true;
  btn.textContent = 'Analisando imagem...';
  renderResults([]);
  qs('#ocr-output').classList.add('hidden');
  setStatus('#scan-status', 'Reconhecendo as letras da capa e buscando possíveis livros...');
  try {
    const body = new FormData();
    body.append('image', uploadedFile);
    const data = await apiRequest('/api/recognize', {method: 'POST', body});
    if (!Array.isArray(data.detected) || !Array.isArray(data.books)) {
      throw new Error('A resposta de reconhecimento não contém listas válidas.');
    }
    const detected = data.detected.filter(entry => entry && typeof entry.text === 'string');
    if (detected.length) {
      qs('#ocr-text').textContent = detected.map(entry => entry.text).join(' · ');
      qs('#ocr-output').classList.remove('hidden');
    }
    renderResults(data.books || []);
    setStatus('#scan-status', data.message || (data.books.length ? `${data.books.length} possível(is) livro(s) encontrado(s). Confirme o correto!` : 'Nenhum livro encontrado. Tente a busca manual.'));
    if (data.books.length === 0 && Array.isArray(data.queries) && data.queries.length) qs('#search-input').value = data.queries[0];
  } catch (error) {
    setStatus('#scan-status', error.message, true);
  } finally {
    btn.disabled = !uploadedFile;
    btn.textContent = '◉ Analisar capa';
  }
});

/**
 * Valida a consulta e executa GET /api/search; os livros recebidos atualizam
 * #search-results e erros HTTP ou de conexão são anunciados em #scan-status.
 */
async function searchManually() {
  const q = qs('#search-input').value.trim();
  if (q.length < 2) {
    setStatus('#scan-status', 'Digite pelo menos duas letras.', true);
    return;
  }
  const btn = qs('#search-btn');
  btn.disabled = true;
  setStatus('#scan-status', `Pesquisando “${q}”...`);
  try {
      const type = qs('#search-type').value;
      const data = await apiRequest(`/api/search?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}`);
    if (!Array.isArray(data.books)) throw new Error('A resposta da busca não contém uma lista de livros.');
    renderResults(data.books);
    setStatus('#scan-status', data.books.length ? `${data.books.length} resultado(s). Confirme o título e adicione.` : 'Nenhum resultado. Experimente outro título.');
  } catch(error) {
    setStatus('#scan-status', error.message, true);
  } finally { btn.disabled = false; }
}
// Clique e tecla Enter acionam a mesma busca manual para manter o comportamento consistente.
qs('#search-btn').addEventListener('click', searchManually);
qs('#search-input').addEventListener('keydown', event => {if (event.key === 'Enter') searchManually();});
/** Ajusta rótulo e exemplo de consulta conforme o tipo de busca selecionado. */
qs('#search-type').addEventListener('change', event => {
  const labels = {title: ['Buscar livro pelo título', 'Ex.: O Hobbit, Harry Potter...'],
    author: ['Buscar livros pelo autor', 'Ex.: Machado de Assis, Tolkien...'],
    isbn: ['Buscar livro pelo ISBN', 'Ex.: 9780547928227']};
  const [label, placeholder] = labels[event.currentTarget.value] || labels.title;
  qs('#search-input').setAttribute('aria-label', label);
  qs('#search-input').placeholder = placeholder;
});

/** Cria controles de meta usando elementos textuais para evitar HTML não confiável. */
function renderGoals(goals) {
  const container = qs('#goals-list');
  container.replaceChildren();
  goals.forEach(goal => {
    const card = make('article', 'goal-card');
    const heading = make('h3', '', `${goal.completed} de ${goal.target} livros concluídos`);
    const period = make('p', 'muted-small', `${goal.start_date} a ${goal.end_date} · faltam ${goal.remaining}`);
    const progress = make('div', 'goal-progress');
    progress.setAttribute('role', 'progressbar');
    progress.setAttribute('aria-valuemin', '0');
    progress.setAttribute('aria-valuemax', '100');
    progress.setAttribute('aria-valuenow', String(goal.progress_percent));
    const fill = make('span', 'goal-progress-fill');
    fill.style.width = `${goal.progress_percent}%`;
    progress.appendChild(fill);
    const actions = make('div', 'goal-actions');
    const edit = make('button', 'btn btn-secondary', 'Editar');
    edit.type = 'button';
    edit.addEventListener('click', () => {
      editingGoalId = goal.id;
      qs('#goal-target').value = goal.target;
      qs('#goal-start').value = goal.start_date;
      qs('#goal-end').value = goal.end_date;
      qs('#goal-submit').textContent = 'Salvar alterações';
      qs('#goal-cancel-edit').classList.remove('hidden');
      qs('#goal-target').focus();
    });
    const remove = make('button', 'btn btn-secondary', 'Excluir');
    remove.type = 'button';
    remove.addEventListener('click', () => deleteGoal(goal));
    actions.append(edit, remove);
    card.append(heading, period, progress, actions);
    container.appendChild(card);
  });
}

/** Consulta GET /api/goals e atualiza indicadores calculados pelo PostgreSQL. */
async function loadGoals() {
  try {
    const data = await apiRequest('/api/goals');
    if (!Array.isArray(data.goals)) throw new Error('A resposta das metas veio em formato inesperado.');
    renderGoals(data.goals);
    return true;
  } catch (error) { setStatus('#goals-status', error.message, true); return false; }
}

/** Envia POST ou PUT para criar/editar uma meta da sessão autenticada. */
async function saveGoal(event) {
  event.preventDefault();
  const payload = {
    target: Number(qs('#goal-target').value),
    start_date: qs('#goal-start').value,
    end_date: qs('#goal-end').value,
  };
  try {
    await apiRequest(editingGoalId ? `/api/goals/${encodeURIComponent(editingGoalId)}` : '/api/goals', {
      method: editingGoalId ? 'PUT' : 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    setStatus('#goals-status', editingGoalId ? 'Meta atualizada.' : 'Meta criada.');
    resetGoalForm();
    await loadGoals();
  } catch (error) { setStatus('#goals-status', error.message, true); }
}

/** Remove meta após confirmação e solicita novamente a lista da conta. */
async function deleteGoal(goal) {
  if (!window.confirm(`Excluir a meta de ${goal.target} livros?`)) return;
  try {
    await apiRequest(`/api/goals/${encodeURIComponent(goal.id)}`, {method: 'DELETE'});
    setStatus('#goals-status', 'Meta removida.');
    await loadGoals();
  } catch (error) { setStatus('#goals-status', error.message, true); }
}

/** Retorna o formulário de meta ao estado de criação. */
function resetGoalForm() {
  editingGoalId = null;
  qs('#goal-form').reset();
  qs('#goal-target').value = '3';
  qs('#goal-start').value = localDateInput(new Date());
  qs('#goal-end').value = localDateInput(new Date(new Date().setMonth(new Date().getMonth() + 1)));
  qs('#goal-submit').textContent = 'Criar meta';
  qs('#goal-cancel-edit').classList.add('hidden');
}

/** Formata uma data do navegador para preencher input date sem conversão UTC. */
function localDateInput(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Exibe somente interesses próprios e conecta cada controle à remoção CSRF. */
function renderPreferences(preferences) {
  const container = qs('#preferences-list');
  container.replaceChildren();
  preferences.forEach(item => {
    const row = make('div', 'preference-row', `${item.category === 'genero' ? 'Gênero' : 'Assunto'}: ${item.value} · nível ${item.level}`);
    const remove = make('button', 'btn btn-secondary', 'Remover');
    remove.type = 'button';
    remove.addEventListener('click', async () => {
      try {
        await apiRequest(`/api/preferences/${encodeURIComponent(item.id)}`, {method: 'DELETE'});
        await loadPreferences();
      } catch (error) { setStatus('#recommend-status', error.message, true); }
    });
    row.appendChild(remove);
    container.appendChild(row);
  });
}

/** Consulta interesses em GET /api/preferences para exibir e orientar recomendações. */
async function loadPreferences() {
  try {
    const data = await apiRequest('/api/preferences');
    if (!Array.isArray(data.preferences)) throw new Error('A resposta de interesses veio em formato inesperado.');
    renderPreferences(data.preferences);
  } catch (error) { setStatus('#recommend-status', error.message, true); }
}

/** Salva preferência privada com CSRF e recarrega a lista de interesses. */
async function savePreference(event) {
  event.preventDefault();
  const payload = {
    category: qs('#preference-category').value,
    value: qs('#preference-value').value.trim(),
    level: Number(qs('#preference-level').value),
  };
  try {
    await apiRequest('/api/preferences', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    qs('#preference-form').reset();
    setStatus('#recommend-status', 'Interesse salvo para as próximas recomendações.');
    await loadPreferences();
  } catch (error) { setStatus('#recommend-status', error.message, true); }
}

qs('#goal-form').addEventListener('submit', saveGoal);
qs('#goal-cancel-edit').addEventListener('click', resetGoalForm);
qs('#preference-form').addEventListener('submit', savePreference);
qs('#progress-status').addEventListener('change', event => {
  if (event.currentTarget.value === 'lendo' && !qs('#progress-started').value) {
    qs('#progress-started').value = localDateInput(new Date());
  }
  if (event.currentTarget.value === 'concluido') {
    if (!qs('#progress-started').value) qs('#progress-started').value = localDateInput(new Date());
    qs('#progress-completed').value = localDateInput(new Date());
    if (qs('#progress-total-pages').value) qs('#progress-pages-read').value = qs('#progress-total-pages').value;
  } else {
    qs('#progress-completed').value = '';
    if (event.currentTarget.value === 'nao_iniciado') {
      qs('#progress-started').value = '';
      qs('#progress-pages-read').value = '0';
    }
  }
});
qs('#save-progress').addEventListener('click', saveReadingProgress);

/**
 * Solicita recomendações associadas à biblioteca da sessão em POST /api/recommend.
 * O backend consulta PostgreSQL e a Open Library; respostas inválidas e falhas
 * são apresentadas em #recommend-status.
 */
qs('#recommend-btn').addEventListener('click', async () => {
  const btn = qs('#recommend-btn');
  btn.disabled = true;
  setStatus('#recommend-status', 'Buscando livros com temas parecidos...');
  try {
    const data = await apiRequest('/api/recommend', {method: 'POST'});
    if (!Array.isArray(data.books)) throw new Error('A resposta de recomendações não contém uma lista de livros.');
    const subjects = Array.isArray(data.subjects) ? data.subjects.filter(subject => typeof subject === 'string') : [];
    renderRecommendations(data.books);
    setStatus('#recommend-status', data.message || `${data.books.length} sugestão(ões) a partir de: ${subjects.join(', ')}.`);
  } catch(error) {
    setStatus('#recommend-status', error.message, true);
  } finally { btn.disabled = library.length === 0; }
});

// A existência da chave legada é detectada sem ler, alterar ou importar seu conteúdo.
try {
  if (localStorage.getItem(STORAGE_KEY) !== null) qs('#legacy-notice').classList.remove('hidden');
} catch (_) { /* A política do navegador pode bloquear a leitura de metadados locais. */ }
resetGoalForm();
loadLibrary();
loadGoals();
loadPreferences();
