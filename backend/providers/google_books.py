"""Acesso opcional ao catálogo público Google Books."""

from __future__ import annotations

import os
import re
from typing import Any

import requests

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "BibliotecaInteligente-DemoAcademico/1.0"})


class GoogleBooksError(Exception):
    """Indica que Google Books devolveu falha ou estrutura inesperada."""


def _api_key() -> str:
    """Obtém chave de configuração sem colocá-la em logs ou respostas.

    Retorno:
        Texto configurado, ou string vazia quando não existe chave.

    Integração:
        O adaptador prioriza variável de ambiente e depois lê somente o campo
        GOOGLE_BOOKS_API_KEY do arquivo `.env` protegido do projeto.

    Tratamento de erros:
        Arquivo ausente ou inacessível desativa a integração sem exceção.
    """
    value = os.environ.get("GOOGLE_BOOKS_API_KEY", "").strip()
    if value:
        return value
    try:
        from backend.database import ENV_FILE
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("GOOGLE_BOOKS_API_KEY="):
                return line.partition("=")[2].strip()
    except OSError:
        return ""
    return ""


def provider_enabled() -> bool:
    """Indica se a integração foi habilitada por credencial local.

    Retorno:
        Valor booleano, sem expor ou registrar o conteúdo da chave.

    Integração:
        O catálogo só consulta este provedor complementar quando a configuração
        GOOGLE_BOOKS_API_KEY existe no ambiente do processo.
    """
    return bool(_api_key())


def _clean_text(value: Any, maximum: int = 4000) -> str | None:
    """Limita texto não confiável recebido do catálogo externo.

    Parâmetros:
        value: campo possivelmente textual da resposta Google Books.
        maximum: quantidade máxima de caracteres preservada.

    Retorno:
        Texto com espaços normalizados ou ``None`` para valor não textual/vazio.

    Integração:
        A normalização ocorre antes que os campos sejam serializados à rota.

    Tratamento de erros:
        Tipos inesperados são descartados sem interromper outros metadados.
    """
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())[:maximum]
    return cleaned or None


def search_metadata(query: str, search_type: str = "title") -> list[dict[str, Any]]:
    """Busca metadados complementares sem criar candidatos independentes.

    Parâmetros:
        query: texto de título, autor ou ISBN enviado pela camada de catálogo.
        search_type: tipo validado pela camada de catálogo.

    Retorno:
        Lista limitada de registros normalizados; vazia quando a integração
        está desativada ou não há itens utilizáveis.

    Integração:
        ``backend.catalogo`` compara ISBNs exatos antes de complementar os
        campos omitidos pela Open Library. Nenhum dado segue direto ao SQL.

    Tratamento de erros:
        Falhas HTTP, timeout, JSON ou campos inesperados geram
        ``GoogleBooksError`` e não apagam o texto obtido por OCR.
    """
    api_key = _api_key()
    if not api_key or search_type not in {"title", "author", "isbn"}:
        return []
    prefix = {"title": "intitle", "author": "inauthor", "isbn": "isbn"}[search_type]
    try:
        response = HTTP.get(
            GOOGLE_BOOKS_URL,
            params={"q": f"{prefix}:{query[:120]}", "maxResults": 8, "key": api_key},
            timeout=(3.05, 8),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise GoogleBooksError("Google Books está temporariamente indisponível.") from error
    if not isinstance(payload, dict):
        raise GoogleBooksError("Google Books retornou dados bibliográficos inválidos.")
    items = payload.get("items", [])
    if not isinstance(items, list):
        if payload.get("totalItems", 0) == 0:
            return []
        raise GoogleBooksError("Google Books retornou dados bibliográficos incompletos.")
    normalized = []
    for item in items[:8]:
        if not isinstance(item, dict) or not isinstance(item.get("volumeInfo"), dict):
            continue
        volume = item["volumeInfo"]
        identifiers = volume.get("industryIdentifiers", [])
        identifiers = identifiers if isinstance(identifiers, list) else []
        isbns = {}
        for identifier in identifiers:
            if isinstance(identifier, dict) and identifier.get("type") in {"ISBN_10", "ISBN_13"}:
                value = identifier.get("identifier")
                if isinstance(value, str):
                    isbns[identifier["type"].lower()] = value[:20]
        authors = volume.get("authors", [])
        authors = [value[:160] for value in authors if isinstance(value, str)][:8] if isinstance(authors, list) else []
        image_links = volume.get("imageLinks", {})
        image_links = image_links if isinstance(image_links, dict) else {}
        published = _clean_text(volume.get("publishedDate"), 20)
        year = None
        if published:
            match = re.match(r"^(\d{4})", published)
            year = int(match.group(1)) if match else None
        categories = volume.get("categories", [])
        page_count = volume.get("pageCount")
        if not isinstance(page_count, int) or isinstance(page_count, bool) or not 1 <= page_count <= 100000:
            page_count = None
        normalized.append({
            "title": _clean_text(volume.get("title"), 500),
            "subtitle": _clean_text(volume.get("subtitle"), 500),
            "authors": authors,
            "description": _clean_text(volume.get("description")),
            "isbn_10": isbns.get("isbn_10"),
            "isbn_13": isbns.get("isbn_13"),
            "language": _clean_text(volume.get("language"), 16),
            "publisher": _clean_text(volume.get("publisher"), 300),
            "year": year,
            "page_count": page_count,
            "subjects": [value[:160] for value in categories if isinstance(value, str)][:16]
            if isinstance(categories, list) else [],
            "cover": _clean_text(image_links.get("thumbnail"), 1000),
            "source": "google_books",
            "source_id": _clean_text(item.get("id"), 200),
        })
    return [record for record in normalized if record["title"]]
