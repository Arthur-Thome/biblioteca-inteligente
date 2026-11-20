"""Acesso e normalização do catálogo bibliográfico Open Library."""

import logging
import re
import threading
import time
import unicodedata
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import requests
from rapidfuzz import fuzz

LOGGER = logging.getLogger(__name__)
OPEN_LIBRARY = "https://openlibrary.org"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BibliotecaInteligente-DemoAcademico/1.0 (educational demo)"})
REQUEST_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


class CatalogError(Exception):
    """Indica que a consulta ou a resposta da Open Library não pôde ser usada."""

    def __init__(self, message: str, *, retry_after: str | None = None):
        """Armazena erro público e intervalo de repetição validado.

        Parâmetros:
            message: texto seguro apresentado pela rota Flask.
            retry_after: intervalo em segundos já limitado, quando existente.

        Retorno:
            Nenhum; a instância preserva os dados para tratamento HTTP.

        Integração:
            As rotas usam `retry_after` no cabeçalho HTTP correspondente.

        Tratamento de erros:
            O conteúdo do catálogo não é concatenado à mensagem pública.
        """
        super().__init__(message)
        self.retry_after = retry_after


def _retry_after_header(value: Any) -> str | None:
    """Converte Retry-After numérico ou data HTTP para segundos limitados.

    Parâmetros:
        value: valor do cabeçalho enviado pela Open Library.

    Retorno:
        Segundos em texto entre zero e 86400, ou ``None`` se inválido.

    Integração:
        `catalog_get` conserva esse intervalo em `CatalogError` para a rota.

    Tratamento de erros:
        Datas malformadas e valores extremos são rejeitados ou limitados.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return str(min(int(stripped), 86400))
    try:
        parsed = parsedate_to_datetime(stripped)
        seconds = max(0, int((parsed - datetime.now(timezone.utc)).total_seconds()))
        return str(min(seconds, 86400))
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_text(value: str) -> str:
    """Normaliza texto removendo acentos e pontuação para comparações.

    Parâmetros:
        value: texto original; valores falsos são tratados como texto vazio.

    Retorno:
        Texto minúsculo, sem diacríticos e com espaços normalizados.

    Integração:
        O pareamento OCR e a seleção de assuntos usam esta função.

    Tratamento de erros:
        Entradas vazias produzem uma string vazia.
    """
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def catalog_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Consulta a API da Open Library com intervalo e timeout limitados.

    Parâmetros:
        path: caminho relativo da API.
        params: parâmetros de consulta codificados pelo Requests.

    Retorno:
        Objeto JSON recebido do catálogo.

    Integração:
        ``search_books`` utiliza a sessão HTTP compartilhada para acessar a API.

    Tratamento de erros:
        Falhas HTTP, de rede ou JSON inválido geram ``CatalogError``.
    """
    global _LAST_REQUEST
    try:
        with REQUEST_LOCK:
            delay = 1.15 - (time.monotonic() - _LAST_REQUEST)
            if delay > 0:
                time.sleep(delay)
            _LAST_REQUEST = time.monotonic()
            response = SESSION.get(f"{OPEN_LIBRARY}{path}", params=params, timeout=13)
        if response.status_code == 429:
            retry_after = _retry_after_header(response.headers.get("Retry-After"))
            raise CatalogError(
                "A Open Library limitou temporariamente as consultas. Tente novamente mais tarde.",
                retry_after=retry_after,
            )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("O catálogo retornou dados inesperados")
        return data
    except CatalogError:
        raise
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Erro na Open Library: %s", exc)
        raise CatalogError("Não foi possível consultar a Open Library. Confira sua internet e tente novamente.") from exc


def canonical_key(key: Any) -> str | None:
    """Valida e reduz uma chave de obra Open Library ao identificador canônico.

    Parâmetros:
        key: valor possivelmente recebido da API ou do navegador.

    Retorno:
        Identificador ``OL...W`` válido ou ``None``.

    Integração:
        A transformação do catálogo e a validação dos livros usam esta regra.

    Tratamento de erros:
        Valores ausentes ou com outro formato são rejeitados sem exceção.
    """
    match = re.search(r"(?:^|/)OL\d+W$", str(key or ""))
    return str(key).split("/")[-1] if match else None


def book_from_doc(doc: dict[str, Any]) -> dict[str, Any] | None:
    """Converte um documento de busca em livro adequado à interface.

    Parâmetros:
        doc: registro retornado pelo endpoint de busca da Open Library.

    Retorno:
        Dicionário bibliográfico compatível com o JavaScript ou ``None``.

    Integração:
        ``search_books`` transforma os registros antes de enviar JSON ao Flask.

    Tratamento de erros:
        Registros sem chave de obra válida ou título são ignorados.
    """
    work = canonical_key(doc.get("key"))
    title = str(doc.get("title") or "").strip()[:500]
    if not work or not title:
        return None
    authors = doc.get("author_name") or []
    authors = authors if isinstance(authors, list) else []
    subjects = doc.get("subject") or []
    subjects = subjects if isinstance(subjects, list) else []
    cover_id = doc.get("cover_i")
    year = doc.get("first_publish_year")
    isbn_values = doc.get("isbn") if isinstance(doc.get("isbn"), list) else []
    isbn_values = [(str(value), normalize_isbn(value)) for value in isbn_values if isinstance(value, (str, int))]
    isbn_10 = next((raw for raw, normalized in isbn_values if normalized and len(normalized) == 10), None)
    isbn_13 = next((raw for raw, normalized in isbn_values if normalized and len(normalized) == 13), None)
    publishers = doc.get("publisher") if isinstance(doc.get("publisher"), list) else []
    languages = doc.get("language") if isinstance(doc.get("language"), list) else []
    subjects_clean = [str(subject)[:160] for subject in subjects[:16] if isinstance(subject, str)]
    raw_description = doc.get("first_sentence")
    if isinstance(raw_description, list):
        raw_description = next((item for item in raw_description if isinstance(item, str)), None)
    description = " ".join(raw_description.split())[:1000] if isinstance(raw_description, str) else None
    subtitle = str(doc.get("subtitle") or "")[:500] or None
    publisher = str(publishers[0])[:300] if publishers and isinstance(publishers[0], str) else None
    language = str(languages[0])[:16] if languages and isinstance(languages[0], str) else None
    raw_page_count = doc.get("number_of_pages_median")
    page_count = raw_page_count if isinstance(raw_page_count, int) and not isinstance(raw_page_count, bool) \
        and 1 <= raw_page_count <= 100000 else None
    metadata_sources = {field: "openlibrary" for field, value in {
        "subtitle": subtitle, "description": description, "publisher": publisher, "language": language,
        "page_count": page_count, "isbn_10": isbn_10, "isbn_13": isbn_13,
    }.items() if value}
    return {
        "id": work,
        "catalog_id": work,
        "title": title,
        "subtitle": subtitle,
        "author": ", ".join(str(author)[:160] for author in authors[:8] if isinstance(author, str)) or "Autor não informado",
        "authors": [str(author)[:160] for author in authors[:8] if isinstance(author, str)],
        "description": description,
        "year": int(year) if str(year).isdigit() else None,
        "publisher": publisher,
        "language": language,
        "page_count": page_count,
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "isbn": isbn_13 or isbn_10,
        "subjects": subjects_clean,
        "genres": subjects_clean[:8],
        "source": "openlibrary",
        "metadata_scope": "work",
        "work_id": work,
        "edition_id": None,
        "metadata_sources": metadata_sources,
        "cover": f"https://covers.openlibrary.org/b/id/{int(cover_id)}-M.jpg"
        if str(cover_id or "").isdigit() else None,
        "url": f"https://openlibrary.org/works/{work}",
    }


@lru_cache(maxsize=256)
def _search_books_cached(
    query: str, limit: int, subject: bool, search_type: str, cache_epoch: int
) -> tuple[dict[str, Any], ...]:
    """Pesquisa obras e converte documentos válidos, mantendo cache limitado.

    Parâmetros:
        query: título ou assunto de pesquisa.
        limit: quantidade máxima solicitada, limitada entre 1 e 24.
        subject: indica se a consulta usa o campo de assunto.
        search_type: ``title``, ``author`` ou ``isbn`` para a busca manual.

    Retorno:
        Tupla de livros normalizados, vazia para consultas curtas.

    Integração:
        OCR, busca manual e recomendações consomem esse catálogo; a rota Flask
        serializa o resultado em JSON para a interface.

    Tratamento de erros:
        Falhas externas são propagadas como ``CatalogError`` para as rotas.
    """
    del cache_epoch
    query = query.strip()[:120]
    if len(query) < 2:
        return ()
    if search_type not in {"title", "author", "isbn"}:
        raise ValueError("O tipo de busca bibliográfica é inválido.")
    if search_type == "isbn":
        normalized_isbn = normalize_isbn(query)
        if not normalized_isbn:
            return ()
        query = normalized_isbn
    params: dict[str, Any] = {
        "fields": "key,title,subtitle,author_name,cover_i,first_publish_year,subject,isbn,publisher,language,number_of_pages_median,first_sentence",
        "limit": max(1, min(int(limit), 24)),
        "subject" if subject else search_type: query,
    }
    data = catalog_get("/search.json", params)
    result_by_work: dict[str, dict[str, Any]] = {}
    documents = data.get("docs", [])
    if not isinstance(documents, list):
        return ()
    used_fallback = False
    # Uma busca estrita pode perder um título quando o OCR troca caracteres.
    # A consulta ampla só é acionada quando nenhum resultado primário se
    # aproxima suficientemente do título; isso limita chamadas extras e evita
    # aceitar materiais que apenas mencionam o texto pesquisado.
    if search_type == "title" and not subject:
        normalized_query = normalize_text(query)
        has_close_title = any(
            isinstance(document, dict)
            and isinstance(document.get("title"), str)
            and fuzz.ratio(normalized_query, normalize_text(document["title"])) >= 90
            for document in documents
        )
        if not has_close_title:
            try:
                fallback_params = dict(params)
                fallback_params.pop("title", None)
                fallback_params["q"] = query
                fallback_data = catalog_get("/search.json", {
                    **fallback_params,
                })
                fallback_docs = fallback_data.get("docs", [])
                if isinstance(fallback_docs, list):
                    documents = [*documents, *(item for item in fallback_docs if isinstance(item, dict))]
                    used_fallback = True
            except CatalogError as error:
                # Resultados da consulta precisa continuam disponíveis se a
                # tentativa tolerante falhar por indisponibilidade externa.
                LOGGER.info("Busca tolerante da Open Library indisponível (%s).", type(error).__name__)
    for document in documents:
        if isinstance(document, dict):
            book = book_from_doc(document)
            if book:
                existing = result_by_work.get(book["id"])
                if existing is None:
                    result_by_work[book["id"]] = book
                else:
                    for field in ("subtitle", "description", "publisher", "language", "page_count", "isbn_10", "isbn_13", "cover"):
                        if not existing.get(field) and book.get(field):
                            existing[field] = book[field]
                            if field in book["metadata_sources"]:
                                existing["metadata_sources"][field] = book["metadata_sources"][field]
    result = list(result_by_work.values())
    if used_fallback:
        # Quando houve busca tolerante, o texto do título ordena os candidatos
        # para que uma obra próxima não fique atrás de um material que apenas
        # contém o texto pesquisado em uma frase maior.
        result.sort(
            key=lambda book: fuzz.ratio(normalize_text(query), normalize_text(book["title"])),
            reverse=True,
        )
    try:
        from backend.providers.google_books import GoogleBooksError, provider_enabled, search_metadata
        if provider_enabled() and result:
            complementary = search_metadata(query, search_type)
            for book in result:
                book_isbns = {normalize_isbn(book.get(field)) for field in ("isbn_10", "isbn_13") if book.get(field)}
                for extra in complementary:
                    extra_isbns = {normalize_isbn(extra.get(field)) for field in ("isbn_10", "isbn_13") if extra.get(field)}
                    if not book_isbns.intersection(extra_isbns):
                        continue
                    provenance = book["metadata_sources"]
                    for field in ("subtitle", "description", "publisher", "language", "page_count", "isbn_10", "isbn_13"):
                        if not book.get(field) and extra.get(field):
                            book[field] = extra[field]
                            provenance[field] = "google_books"
                    book["edition_id"] = extra.get("source_id")
                    book["edition_source"] = "google_books" if book["edition_id"] else None
                    if book["edition_id"]:
                        book["metadata_scope"] = "work_and_edition"
                    if not book.get("isbn"):
                        book["isbn"] = book.get("isbn_13") or book.get("isbn_10")
                    break
    except GoogleBooksError as error:
        LOGGER.info("Complemento Google Books indisponível (%s).", type(error).__name__)
    return tuple(result)


def search_books(
    query: str, limit: int = 8, subject: bool = False, search_type: str = "title"
) -> tuple[dict[str, Any], ...]:
    """Consulta o cache de catálogo com validade temporal de uma hora.

    Parâmetros:
        query: texto submetido para busca bibliográfica.
        limit: limite de resultados encaminhado à função interna.
        subject: indica busca por assunto para recomendações.
        search_type: tipo de consulta manual validado pela camada interna.

    Retorno:
        Tupla com registros normalizados e compatíveis com as rotas atuais.

    Integração:
        Rotas Flask, recomendações e reconhecimento compartilham este cache
        limitado a 256 combinações; a janela horária expira resultados antigos.

    Tratamento de erros:
        Erros de provedores permanecem tipados e propagam às rotas chamadoras.
    """
    one_hour_bucket = int(time.time() // 3600)
    return _search_books_cached(query, limit, subject, search_type, one_hour_bucket)


search_books.cache_clear = _search_books_cached.cache_clear


def normalize_isbn(value: Any) -> str | None:
    """Normaliza ISBN para comparação exata entre registros de provedores.

    Parâmetros:
        value: identificador recebido de fonte bibliográfica externa.

    Retorno:
        Sequência de dígitos e X, ou ``None`` quando o formato é inválido.

    Integração:
        A complementação do Google Books usa a comparação sem pontuação para
        impedir mistura de obras ou edições distintas.
    """
    normalized = re.sub(r"[^0-9Xx]", "", str(value or "")).upper()
    if len(normalized) == 13 and normalized.isdigit():
        checksum = sum(int(character) * (1 if index % 2 == 0 else 3)
                       for index, character in enumerate(normalized[:12]))
        return normalized if (10 - checksum % 10) % 10 == int(normalized[12]) else None
    if len(normalized) == 10 and normalized[:9].isdigit() and normalized[-1] in "0123456789X":
        checksum = sum((10 - index) * int(character) for index, character in enumerate(normalized[:9]))
        check_digit = 10 if normalized[-1] == "X" else int(normalized[-1])
        return normalized if (checksum + check_digit) % 11 == 0 else None
    return None
