"""Prepara arquivos estáticos locais para a CDN Vercel.

Retorno:
    Código de saída zero quando todos os ativos de interface são copiados.

Integração:
    O hook de build definido em pyproject.toml replica `static/` em
    `public/static/`; a fábrica Flask local continua servindo `static/`.

Tratamento de erros:
    Falhas de leitura ou gravação interrompem o build para evitar publicação
    sem CSS ou JavaScript.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "static"
DESTINATION = ROOT / "public" / "static"


def main() -> None:
    """Copia os ativos frontend para o diretório estático da Vercel.

    Retorno:
        Nenhum valor; os arquivos de origem não são removidos ou alterados.

    Integração:
        Vercel distribui `public/**` pela CDN, enquanto o Flask local mantém
        o diretório `static/` como origem dos mesmos arquivos.

    Tratamento de erros:
        Diretório de origem ausente ou falha de cópia interrompe a execução.
    """
    if not SOURCE.is_dir():
        raise FileNotFoundError("O diretório de ativos frontend static/ não foi encontrado.")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for source_file in SOURCE.rglob("*"):
        if source_file.is_file():
            relative_path = source_file.relative_to(SOURCE)
            destination_file = DESTINATION / relative_path
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination_file)


if __name__ == "__main__":
    main()
