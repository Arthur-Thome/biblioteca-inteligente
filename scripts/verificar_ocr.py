"""Confirma que RapidOCR carrega os modelos locais sem depender da rede."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.visao_computacional import OCR_MODEL_DIR, extract_cover_text


def main() -> int:
    """Executa OCR em texto sintético enquanto bloqueia conexões de saída.

    Retorno:
        Código zero quando há texto reconhecido com os modelos locais.

    Tratamento de erros:
        Modelo ausente ou tentativa de rede resulta em diagnóstico sem substituir
        o OCR por uma resposta simulada.
    """
    missing = [
        name
        for name in (
            "PP-OCRv6_det_small.onnx",
            "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
            "PP-OCRv6_rec_small.onnx",
        )
        if not (OCR_MODEL_DIR / name).is_file()
    ]
    if missing:
        print("Modelos OCR locais ausentes: " + ", ".join(missing))
        return 1

    def block_network(*_args, **_kwargs):
        raise OSError("A rede foi bloqueada pelo teste local de OCR.")

    original_connect = socket.socket.connect
    socket.socket.connect = block_network
    try:
        image = Image.new("RGB", (1000, 300), "white")
        draw = ImageDraw.Draw(image)
        font_path = "C:/Windows/Fonts/arial.ttf"
        font = ImageFont.truetype(font_path, 78)
        draw.text((35, 80), "THE HOBBIT", fill="black", font=font)
        import io

        stream = io.BytesIO()
        image.save(stream, format="PNG")
        found = extract_cover_text(stream.getvalue())
    finally:
        socket.socket.connect = original_connect

    text = " ".join(entry["text"] for entry in found).casefold()
    if "hobbit" not in text:
        print("Os modelos locais não reconheceram o texto de verificação.")
        return 1
    print("RapidOCR reconheceu texto usando os modelos locais, sem conexão de rede.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
