"""Preparação de imagens de capas e extração local de texto por RapidOCR."""

import io
import math
import re
import threading
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageOps
from rapidfuzz import fuzz

from backend.catalogo import normalize_text

OCR_LOCK = threading.Lock()
_OCR_ENGINE: Any | None = None
MIN_OCR_MATCH_SCORE = 50.0
OCR_MODEL_DIR = Path(__file__).resolve().parents[1] / "models_ocr"


def get_ocr_engine() -> Any:
    """Inicializa RapidOCR apenas quando a primeira imagem é analisada.

    Retorno:
        Instância pronta para inferência OCR.

    Integração:
        ``extract_cover_text`` usa o mecanismo; a rota o inicializa antes da
        inferência. O parâmetro oficial ``Global.model_root_dir`` direciona o
        RapidOCR aos modelos mantidos na pasta local ``models_ocr``.

    Tratamento de erros:
        Erros de importação ou inicialização são propagados à rota, que responde
        com mensagem controlada sem expor detalhes internos ao navegador.
    """
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        with OCR_LOCK:
            if _OCR_ENGINE is None:
                from rapidocr import RapidOCR

                _OCR_ENGINE = RapidOCR(
                    params={"Global.model_root_dir": str(OCR_MODEL_DIR)}
                )
    return _OCR_ENGINE


def extract_cover_text(image_data: bytes) -> list[dict[str, Any]]:
    """Prepara a imagem, ordena caixas e extrai textos com confiança válida.

    Parâmetros:
        image_data: bytes de uma imagem previamente verificada pela rota.

    Retorno:
        Até 30 registros com ``text`` e ``confidence``, ordenados pela posição
        vertical e horizontal quando as caixas RapidOCR estão disponíveis.

    Integração:
        Usa Pillow e NumPy para preparar a imagem e RapidOCR para inferência;
        a rota combina o texto com a pesquisa bibliográfica.

    Tratamento de erros:
        Erros de decodificação, dependências ou inferência são propagados para
        que a rota Flask apresente erro HTTP controlado.
    """
    with Image.open(io.BytesIO(image_data)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1700, 1700))
        image = ImageEnhance.Contrast(image).enhance(1.18)
        import numpy as np

        bitmap = np.array(image)
    # A inicialização usa o mesmo lock; por isso, ela ocorre antes do lock exclusivo da inferência.
    engine = get_ocr_engine()
    with OCR_LOCK:
        ocr_result = engine(bitmap)
    texts = list(ocr_result.txts or [])
    scores = list(ocr_result.scores or [])
    raw_boxes = getattr(ocr_result, "boxes", None)
    boxes = list(raw_boxes) if raw_boxes is not None else []
    detections = []
    for index, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        try:
            score = float(scores[index]) if index < len(scores) else 0.0
        except (TypeError, ValueError, OverflowError):
            continue
        if not text or not math.isfinite(score) or not 0.30 <= score <= 1.0:
            continue

        # Cada caixa oficial possui quatro pontos. Coordenadas inválidas deixam
        # a detecção na posição original, preservando a resposta do mecanismo.
        position = (float("inf"), float("inf"))
        if index < len(boxes):
            try:
                points = np.asarray(boxes[index], dtype=float)
                if points.shape == (4, 2) and np.isfinite(points).all():
                    position = (float(points[:, 1].min()), float(points[:, 0].min()))
            except (TypeError, ValueError):
                pass
        detections.append((position, index, {"text": text, "confidence": round(score, 3)}))

    # A ordenação espacial só ocorre quando todas as caixas úteis são válidas;
    # qualquer caixa ausente ou malformada preserva a ordem original do motor.
    if all(math.isfinite(position[0]) and math.isfinite(position[1]) for position, _, _ in detections):
        detections.sort(key=lambda item: (item[0][0], item[0][1], item[1]))
    else:
        detections.sort(key=lambda item: item[1])
    return [entry for _, _, entry in detections[:30]]


def suggest_search_queries(lines: list[str] | list[dict[str, Any]]) -> list[str]:
    """Prioriza linhas e combinações OCR pela confiança fornecida pelo modelo.

    Parâmetros:
        lines: textos reconhecidos ou registros ``text``/``confidence`` do OCR.

    Retorno:
        Até três consultas distintas e limitadas para o catálogo.

    Integração:
        A rota ``/api/recognize`` passa as consultas a ``search_books``; os
        registros preservam a confiança por linha sem tratá-la como certeza.

    Tratamento de erros:
        Lista vazia ou linhas sem conteúdo útil produzem lista vazia.
    """
    detections: list[tuple[str, float, int]] = []
    for index, item in enumerate(lines):
        if isinstance(item, dict):
            line = item.get("text", "")
            try:
                confidence = float(item.get("confidence", 0.5))
            except (TypeError, ValueError, OverflowError):
                confidence = 0.0
        else:
            line = item
            confidence = 0.5
        if not isinstance(line, str) or not math.isfinite(confidence):
            continue
        line = re.sub(r"\s+", " ", line).strip()
        if len(normalize_text(line)) >= 3:
            detections.append((line, min(1.0, max(0.0, confidence)), index))
    if not detections:
        return []

    candidates: list[tuple[float, str, int]] = [
        (confidence, line, index) for line, confidence, index in detections
    ]
    # Combina somente linhas próximas; a média reduz o efeito de uma detecção
    # confiável quando a linha vizinha contém ruído ou texto editorial.
    for window_size in (2, 3):
        for start in range(len(detections) - window_size + 1):
            window = detections[start:start + window_size]
            query = " ".join(item[0] for item in window)
            confidence = sum(item[1] for item in window) / window_size
            candidates.append((confidence + 0.008 * (window_size - 1), query, window[0][2]))

    candidates.sort(key=lambda item: (-item[0], -len(normalize_text(item[1])), item[2]))
    seen: set[str] = set()
    output = []
    for _, term, _ in candidates:
        term = term[:105]
        normalized = normalize_text(term)
        if normalized not in seen and 4 <= len(normalized) <= 105:
            output.append(term)
            seen.add(normalized)
        if len(output) == 3:
            break
    return output


def author_match_strength(book: dict[str, Any], text: str) -> float:
    """Calcula a proporção dos tokens editoriais de autor recuperados no OCR.

    Parâmetros:
        book: candidato com campo ``author`` ou ``authors`` textual.
        text: texto OCR combinado da imagem.

    Retorno:
        Maior proporção entre zero e um; zero indica ausência de correspondência.

    Integração:
        A rota reconhece se a imagem contém evidência de autor antes de aplicar
        uma penalidade heurística a candidatos com autoria incompatível.

    Tratamento de erros:
        Campos ausentes ou vazios retornam ``False``.
    """
    raw_authors = book.get("authors")
    if not isinstance(raw_authors, list):
        raw_authors = [book.get("author", "")]
    whole = normalize_text(text)
    strengths = []
    for raw_author in raw_authors:
        author = normalize_text(str(raw_author or ""))
        tokens = [token for token in author.split() if len(token) >= 3]
        compact = "".join(author.split())
        matched = sum(token in whole.split() for token in tokens)
        if compact and len(compact) >= 6 and compact in "".join(whole.split()):
            matched = max(matched, len(tokens))
        if tokens:
            strengths.append(matched / len(tokens))
    return max(strengths, default=0.0)


def author_matches_ocr(book: dict[str, Any], text: str) -> bool:
    """Indica se algum token de autor também aparece no texto da capa.

    Parâmetros:
        book: candidato com campo ``author`` ou ``authors`` textual.
        text: texto OCR combinado da imagem.

    Retorno:
        Valor booleano que indica correspondência textual de autor.

    Integração:
        A rota usa este indicador para saber se a classificação pode considerar
        diferenças de autoria entre candidatos de título semelhante.

    Tratamento de erros:
        Campos ausentes ou vazios retornam ``False``.
    """
    return author_match_strength(book, text) > 0


def score_ocr_match(book: dict[str, Any], text: str, *, penalize_author_mismatch: bool = False) -> float:
    """Calcula pontuação heurística do título e reforço limitado do autor.

    Parâmetros:
        book: livro normalizado com ``title`` e, opcionalmente, ``author``.
        text: texto OCR combinado da imagem.
        penalize_author_mismatch: aplica desconto quando outra autoria foi
            reconhecida claramente no mesmo conjunto de candidatos.

    Retorno:
        Pontuação de ordenação entre 0 e 100, arredondada a uma casa decimal;
        o valor não representa probabilidade estatística.

    Integração:
        A rota de reconhecimento usa RapidFuzz para ordenar candidatos da API;
        a presença de palavras do autor só ajusta a pontuação do título.

    Tratamento de erros:
        Título ou texto normalizado vazio resulta em pontuação zero. Palavras
        funcionais isoladas recebem penalização para reduzir falsos positivos.

    Decisão de classificação:
        A rota só apresenta candidatos com pontuação mínima 50. O reforço por
        autor é limitado e não é aplicado como evidência independente.
    """
    title = normalize_text(str(book.get("title") or ""))
    whole = normalize_text(text)
    if not title or not whole:
        return 0.0
    tokens = title.split()
    title_score = 0.75 * fuzz.token_set_ratio(title, whole) + 0.25 * fuzz.partial_ratio(title, whole)

    # Um título curto não recebe correspondência alta por uma palavra comum
    # isolada. Obras com título de uma palavra precisam de correspondência exata.
    common_single_word_titles = {"a", "an", "as", "do", "da", "de", "the", "of", "to"}
    if len(tokens) == 1 and (title in common_single_word_titles or title not in whole.split()):
        title_score *= 0.35

    # O autor só ajusta uma correspondência de título já existente; não consegue
    # elevar sozinho uma obra sem evidência textual suficiente na capa.
    author_strength = author_match_strength(book, text)
    if author_strength:
        title_score = min(100.0, title_score + 12.0 * author_strength)
    elif penalize_author_mismatch:
        # A divergência só pesa quando pelo menos um candidato forneceu indício
        # textual de autor; sem esse contexto, título semelhante fica neutro.
        title_score = max(0.0, title_score - 18.0)
    return round(title_score, 1)
