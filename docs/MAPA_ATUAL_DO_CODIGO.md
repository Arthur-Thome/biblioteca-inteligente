# Mapa atual do código

Este documento registra a estrutura após a refatoração da Etapa 2. O diagnóstico inicial e o mapa anterior permanecem descritos historicamente em `DIAGNOSTICO_INICIAL.md`; os detalhes de contratos e fluxos completos estão em `INTEGRACAO_FRONTEND_BACKEND.md`.

## Estrutura

```text
app.py
backend/
  __init__.py               fábrica Flask e registro das rotas
  routes.py                 página e APIs HTTP
  catalogo.py               cliente Open Library e transformação bibliográfica
  visao_computacional.py    preparação de imagem, OCR e pontuação textual
  recomendacoes.py          escolha de assuntos e classificação dos livros
  validacoes.py              validação do upload e dos livros recebidos em JSON
templates/index.html         tela única e seletores usados pelo JavaScript
static/style.css             estilos por componente e breakpoints responsivos
static/app.js                eventos, câmera, chamadas HTTP, renderização e localStorage
tests/test_app.py             testes Flask e serviços com dependências simuladas
```

## Fluxo entre módulos

- `app.py` chama `backend.create_app`; a fábrica configura templates/estáticos, limite de corpo e blueprint.
- `backend.routes` recebe HTTP e coordena validações, OCR, catálogo e recomendações.
- `backend.validacoes` verifica bytes JPEG/PNG/WEBP, dimensões e estrutura de livros do JSON.
- `backend.visao_computacional` prepara imagem com Pillow/NumPy, executa RapidOCR, formula consultas e compara texto com RapidFuzz.
- `backend.catalogo` consulta Open Library, normaliza documentos, limita chamadas e armazena resultados em cache.
- `backend.recomendacoes` usa assuntos dos livros enviados pelo navegador e solicita candidatos ao catálogo.
- `templates/index.html` carrega CSS e JavaScript. `static/app.js` chama `/api/recognize`, `/api/search` e `/api/recommend`, atualizando elementos por IDs e inserindo texto com `textContent`.
- Cadastro, consulta e remoção da biblioteca ocorrem no navegador em `localStorage`, chave `estante-livros-v1`; nenhuma rota grava a biblioteca.

## Rotas atuais

| Rota | Responsabilidade |
|---|---|
| `GET /` | Entrega `templates/index.html`. |
| `GET /api/health` | Informa os serviços configurados sem testar disponibilidade real. |
| `GET /api/search?q=...` | Pesquisa títulos na Open Library. |
| `POST /api/recognize` | Recebe multipart `image`, valida, executa OCR e tenta identificar candidatos. |
| `POST /api/recommend` | Recebe JSON `{ "books": [...] }`, valida e busca recomendações por assunto. |

## Persistência e limites

O estado de biblioteca fica apenas em `localStorage`. Não há banco, login, progresso, metas ou integração Google Books. A estrutura do objeto local foi preservada nesta etapa para não descartar coleções existentes. A arquitetura e limitações constam em `ARQUITETURA.md`; a ligação elemento-a-elemento consta em `INTEGRACAO_FRONTEND_BACKEND.md`.
