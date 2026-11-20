"""Executa um conjunto pequeno e reproduzível de consultas bibliográficas reais."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.catalogo import CatalogError, canonical_key, catalog_get, normalize_text, search_books

CASES = (
    {"type": "title", "query": "The Hobbit", "expected": "The Hobbit"},
    {"type": "title", "query": "Harry Potter and the Philosopher's Stone",
     "expected": "Harry Potter and the Philosopher's Stone"},
    {"type": "title", "query": "Dom Casmurro", "expected": "Dom Casmurro"},
    {"type": "title", "query": "Dom Casmúrro", "expected": "Dom Casmurro"},
    {"type": "title", "query": "Philosopher's Stone", "expected": "Harry Potter and the Philosopher's Stone"},
    {"type": "title", "query": "The Hobit", "expected": "The Hobbit"},
    {"type": "title", "query": "Hamlet", "expected": "Hamlet"},
    {"type": "author", "query": "J. R. R. Tolkien", "expected": "The Hobbit"},
    {"type": "isbn", "query": "9780547928227", "expected": "The Hobbit"},
)


def _legacy_titles(query: str) -> list[str]:
    """Reproduz a busca anterior, limitada aos campos que a versão entregava.

    Parâmetros:
        query: consulta encaminhada pelo código anterior ao parâmetro geral `q`.

    Retorno:
        Títulos válidos na ordem devolvida pelo endpoint Open Library.

    Integração:
        Consulta a mesma Search API e o mesmo catálogo externo usados no ensaio
        atual, sem chamar rotas ou serviços não oficiais.

    Tratamento de erros:
        Falhas do catálogo propagam `CatalogError` ao relatório pareado.
    """
    payload = catalog_get("/search.json", {
        "fields": "key,title,author_name,cover_i,first_publish_year,subject",
        "limit": 8,
        "q": query[:120],
    })
    documents = payload.get("docs", [])
    if not isinstance(documents, list):
        return []
    titles = []
    for document in documents:
        if not isinstance(document, dict) or not canonical_key(document.get("key")):
            continue
        title = document.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
    return titles


def _measure(titles: list[str], expected: str) -> dict[str, object]:
    """Calcula Top-1 e Recall@3 sem confundir semelhança com certeza.

    Parâmetros:
        titles: títulos em ordem de catálogo.
        expected: título esperado no manifesto de avaliação.

    Retorno:
        Dicionário com três primeiros títulos e indicadores booleanos.
    """
    normalized = normalize_text(expected)
    positions = [index for index, title in enumerate(titles, 1)
                 if fuzz.ratio(normalized, normalize_text(title)) >= 90]
    return {
        "titulos_top3": titles[:3],
        "primeiro_resultado": titles[0] if titles else None,
        "correto_em_1o": 1 in positions,
        "correto_no_top3": any(index <= 3 for index in positions),
    }


def evaluate_catalog() -> dict[str, object]:
    """Compara consultas legadas e atuais ao vivo no mesmo conjunto pequeno.

    Retorno:
        Objeto JSON antes/depois com Top-1, Recall@3, latência e falhas observadas.

    Integração:
        Cada caso chama uma vez a consulta antiga e uma vez a tipada atual; ambas
        acessam Open Library. O adaptador atual pode consultar Google Books se
        houver chave local configurada.

    Tratamento de erros:
        Falhas externas ficam registradas por consulta; nenhum resultado é
        inventado para completar as métricas.
    """
    records = []
    for case in CASES:
        record: dict[str, object] = dict(case)
        for label, callback in (("antes", lambda: _legacy_titles(str(case["query"]))),
                                ("depois", lambda: [str(book["title"]) for book in search_books(
                                    str(case["query"]), 8, search_type=str(case["type"]))])):
            started = time.perf_counter()
            try:
                titles = callback()
                record[label] = {
                    **_measure(titles, str(case["expected"])),
                    "tempo_segundos": round(time.perf_counter() - started, 3),
                }
            except CatalogError as error:
                record[label] = {
                    "erro": str(error),
                    "tempo_segundos": round(time.perf_counter() - started, 3),
                }
        records.append(record)
    summaries = {}
    for label in ("antes", "depois"):
        successful = [record[label] for record in records
                      if isinstance(record[label], dict) and "erro" not in record[label]]
        durations = [float(record["tempo_segundos"]) for record in successful]
        summaries[label] = {
            "consultas_com_resposta": len(successful),
            "consultas_com_falha": len(records) - len(successful),
            "top1_corretos": sum(bool(record["correto_em_1o"]) for record in successful),
            "recall_at_3": sum(bool(record["correto_no_top3"]) for record in successful),
            "mediana_segundos": round(statistics.median(durations), 3) if durations else None,
        }
    return {
        "casos": records,
        "resumo": summaries,
    }


def main() -> int:
    """Imprime métricas observadas sem alterar dados PostgreSQL.

    Retorno:
        Código zero quando o ensaio produz saída; a indisponibilidade externa
        permanece representada no relatório individual.

    Integração:
        O script usa o Python de `.venv` e executa buscas reais de baixo volume.
    """
    print(json.dumps(evaluate_catalog(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
