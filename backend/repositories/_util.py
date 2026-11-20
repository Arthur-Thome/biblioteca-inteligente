"""Validações comuns aos repositórios PostgreSQL."""

from __future__ import annotations

import re


def normalizar_texto(valor: str, *, maximo: int, campo: str) -> str:
    """Remove espaços laterais e verifica texto obrigatório e seu limite.

    Parâmetros:
        valor: entrada textual recebida pelo repositório.
        maximo: quantidade máxima de caracteres aceita pelo modelo.
        campo: nome funcional do campo usado na mensagem de validação.

    Retorno:
        Texto com espaços externos removidos.

    Tratamento de erros:
        Valor ausente, vazio ou excedente produz `ValueError`.
    """
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser texto.")
    resultado = valor.strip()
    if not resultado or len(resultado) > maximo:
        raise ValueError(f"{campo} deve conter entre 1 e {maximo} caracteres.")
    return resultado


def normalizar_isbn(valor: str | None) -> str | None:
    """Converte ISBN opcional para forma compacta usada pela restrição única.

    Parâmetros:
        valor: ISBN informado pelo catálogo ou pela camada chamadora.

    Retorno:
        ISBN apenas com dígitos e X maiúsculo, ou `None` quando ausente.

    Tratamento de erros:
        Formatos com caracteres restantes ou comprimento inesperado são
        rejeitados; o banco também protege a unicidade normalizada.
    """
    if valor is None or not valor.strip():
        return None
    resultado = re.sub(r"[^0-9Xx]", "", valor).upper()
    if len(resultado) not in (10, 13):
        raise ValueError("ISBN deve conter dez ou treze caracteres válidos.")
    return resultado
