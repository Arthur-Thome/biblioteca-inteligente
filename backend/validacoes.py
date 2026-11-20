"""Validações de entradas HTTP e dados bibliográficos recebidos do navegador."""

import io
from typing import Any

from PIL import Image, UnidentifiedImageError


def validate_image_bytes(image_data: bytes) -> bool:
    """Confirma que os bytes representam uma imagem reconhecida pelo Pillow.

    Parâmetros:
        image_data: conteúdo binário recebido no upload.

    Retorno:
        ``True`` quando o formato pode ser verificado; caso contrário, ``False``.

    Integração:
        A rota de reconhecimento aplica esta validação antes de inicializar o OCR.

    Tratamento de erros:
        Formatos inválidos, arquivos truncados e bombas de descompressão são
        convertidos em resultado negativo para permitir uma resposta HTTP 400.
    """
    try:
        with Image.open(io.BytesIO(image_data)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                return False
            if image.width * image.height > 40_000_000:
                return False
            image.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return False


def valid_books(items: Any) -> list[dict[str, Any]]:
    """Normaliza os livros enviados pelo navegador para o serviço de recomendação.

    Parâmetros:
        items: valor recebido na propriedade ``books`` do JSON.

    Retorno:
        Lista limitada de livros com identificador válido e campos tipados.

    Integração:
        A rota ``/api/recommend`` encaminha o resultado para o serviço de
        recomendações; não há leitura de banco de dados nesta versão.

    Tratamento de erros:
        Tipos incorretos, identificadores inválidos e campos malformados são
        ignorados sem interromper o processamento dos demais itens.
    """
    from backend.catalogo import canonical_key

    if not isinstance(items, list):
        return []

    clean: list[dict[str, Any]] = []
    for obj in items[:40]:
        if not isinstance(obj, dict):
            continue
        book_id = canonical_key(obj.get("id"))
        if not book_id:
            continue

        raw_subjects = obj.get("subjects")
        subjects = raw_subjects if isinstance(raw_subjects, list) else []
        clean_subjects = [subject[:80] for subject in subjects if isinstance(subject, str)][:16]
        author = obj.get("author")
        clean.append({
            "id": book_id,
            "subjects": clean_subjects,
            "author": author[:160] if isinstance(author, str) else "",
        })
    return clean
