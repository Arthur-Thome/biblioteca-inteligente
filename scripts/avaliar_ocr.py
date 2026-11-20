"""Executa a avaliação reproduzível das capas locais com RapidOCR e catálogo."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.catalogo import CatalogError, normalize_text, search_books
from backend.visao_computacional import (
    author_matches_ocr,
    author_match_strength,
    extract_cover_text,
    score_ocr_match,
    suggest_search_queries,
)

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "ocr"


def evaluate(*, include_catalog: bool = True) -> list[dict[str, object]]:
    """Mede texto, correspondência bibliográfica e tempo por imagem.

    Parâmetros:
        include_catalog: consulta Open Library quando verdadeiro; requer internet.

    Retorno:
        Lista de registros com resultado observado e métricas reproduzíveis.

    Integração:
        Lê o manifesto do conjunto local, chama extract_cover_text e opcionalmente
        consulta search_books, sem enviar a imagem ao serviço externo.

    Tratamento de erros:
        Falha da Open Library é registrada no campo ``erro_catalogo`` e não apaga
        o texto OCR; imagem ausente ou inválida interrompe a avaliação.
    """
    manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for case in manifest:
        image_path = FIXTURE_DIR / case["imagem"]
        image_data = image_path.read_bytes()

        # A primeira inferência carrega os modelos; o aquecimento é separado da
        # mediana para que o tempo represente o processamento já inicializado.
        extract_cover_text(image_data)
        durations: list[float] = []
        detections: list[dict[str, object]] = []
        for _ in range(3):
            started = time.perf_counter()
            detections = extract_cover_text(image_data)
            durations.append(time.perf_counter() - started)

        recognized = " ".join(str(item["text"]) for item in detections)
        expected_title = str(case["titulo_esperado"])
        expected_author = str(case.get("autor_esperado") or "")
        title_recoverable = fuzz.partial_ratio(
            normalize_text(expected_title), normalize_text(recognized)
        ) >= 80

        record: dict[str, object] = {
            "imagem": case["imagem"],
            "titulo_esperado": expected_title,
            "autor_esperado": expected_author,
            "texto_extraido": [item["text"] for item in detections],
            "titulo_recuperavel_no_ocr": title_recoverable,
            "autor_recuperavel_no_ocr": bool(expected_author) and (
                fuzz.partial_ratio(normalize_text(expected_author), normalize_text(recognized)) >= 75
            ),
            "tempo_mediano_segundos": round(statistics.median(durations), 3),
            "consultas": suggest_search_queries(detections),
        }

        if include_catalog:
            try:
                catalog_candidates: dict[str, dict[str, object]] = {}
                for query in record["consultas"]:
                    for book in search_books(str(query), 8):
                        catalog_candidates.setdefault(book["id"], book)
                author_evidence = any(
                    author_matches_ocr(book, recognized) for book in catalog_candidates.values()
                )
                candidates: dict[str, dict[str, object]] = {}
                for book in catalog_candidates.values():
                    score = score_ocr_match(
                        book, recognized, penalize_author_mismatch=author_evidence
                    )
                    if score >= 50 and (
                        book["id"] not in candidates or score > candidates[book["id"]]["pontuacao"]
                    ):
                        candidates[book["id"]] = {**book, "pontuacao": score}
                ranked = sorted(
                    candidates.values(),
                    key=lambda item: (
                        -float(item["pontuacao"]), -author_match_strength(item, recognized), str(item["title"])
                    ),
                )[:8]
                expected_normalized = normalize_text(expected_title)
                correct_positions = [
                    position for position, book in enumerate(ranked, 1)
                    if fuzz.ratio(expected_normalized, normalize_text(str(book["title"]))) >= 90
                ]
                record.update({
                    "primeiro_candidato": ranked[0]["title"] if ranked else None,
                    "autor_primeiro_candidato": ranked[0]["author"] if ranked else None,
                    "correto_entre_candidatos": bool(correct_positions),
                    "correto_em_1o": 1 in correct_positions,
                    "correto_no_top_3": any(position <= 3 for position in correct_positions),
                    "candidatos": [
                        {"titulo": book["title"], "autor": book["author"], "pontuacao_heuristica": book["pontuacao"]}
                        for book in ranked
                    ],
                })
            except CatalogError as error:
                record["erro_catalogo"] = str(error)
        records.append(record)
    return records


def main() -> int:
    """Apresenta resultados sem imagem ou credenciais na saída.

    Parâmetros:
        Nenhum; os argumentos opcionais controlam apenas o acesso ao catálogo.

    Retorno:
        Código zero após avaliação concluída e não zero quando a execução falha.

    Integração:
        O script é executado pelo ambiente virtual e consome modelos locais.

    Tratamento de erros:
        Erros de arquivo e inferência são exibidos pelo interpretador; erros do
        catálogo são registrados por imagem no JSON de saída.
    """
    parser = argparse.ArgumentParser(description="Avalia OCR nas capas do conjunto local.")
    parser.add_argument(
        "--sem-catalogo", action="store_true",
        help="executa somente RapidOCR e não acessa a Open Library",
    )
    args = parser.parse_args()
    print(json.dumps(evaluate(include_catalog=not args.sem_catalogo), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
