"""Preferências simples de assunto e gênero delimitadas por usuário."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Preferencia
from backend.repositories._util import normalizar_texto

CATEGORIAS_VALIDAS = {"genero", "assunto"}


def criar_preferencia(
    session: Session,
    *,
    usuario_id: UUID,
    categoria: str,
    valor: str,
    nivel: int = 3,
) -> Preferencia:
    """Registra preferência normalizada e ligada a uma conta específica.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário da preferência.
        categoria: `genero` ou `assunto`.
        valor: texto de interesse exibido e usado em recomendações futuras.
        nivel: intensidade inteira de 1 a 5.

    Retorno:
        Preferência persistida.

    Tratamento de erros:
        Categoria, texto ou nível inválido produz `ValueError`; duplicações são
        protegidas pela chave única usuário/categoria/valor normalizado.
    """
    category = categoria.strip().casefold() if isinstance(categoria, str) else ""
    if category not in CATEGORIAS_VALIDAS or not 1 <= nivel <= 5:
        raise ValueError("Categoria ou nível de preferência inválido.")
    display_value = normalizar_texto(valor, maximo=160, campo="Preferência")
    preference = Preferencia(
        usuario_id=usuario_id,
        categoria=category,
        valor=display_value,
        valor_normalizado=display_value.casefold(),
        nivel=nivel,
    )
    session.add(preference)
    session.flush()
    return preference


def listar_preferencias(session: Session, *, usuario_id: UUID) -> list[Preferencia]:
    """Lista somente preferências pertencentes à conta indicada.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário obrigatório.

    Retorno:
        Preferências ordenadas por categoria e valor normalizado.
    """
    return list(
        session.scalars(
            select(Preferencia)
            .where(Preferencia.usuario_id == usuario_id)
            .order_by(Preferencia.categoria, Preferencia.valor_normalizado)
        )
    )


def remover_preferencia(session: Session, *, usuario_id: UUID, preferencia_id: UUID) -> bool:
    """Remove preferência somente quando UUID e proprietário coincidem.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        preferencia_id: UUID da preferência.

    Retorno:
        `True` para uma exclusão própria; `False` quando ausente ou de terceiro.
    """
    preference = session.scalar(
        select(Preferencia).where(
            Preferencia.id == preferencia_id,
            Preferencia.usuario_id == usuario_id,
        )
    )
    if preference is None:
        return False
    session.delete(preference)
    session.flush()
    return True


def atualizar_nivel_preferencia(
    session: Session, *, usuario_id: UUID, preferencia_id: UUID, nivel: int
) -> Preferencia | None:
    """Atualiza intensidade apenas para preferência do proprietário.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        preferencia_id: UUID da preferência.
        nivel: intensidade inteira de 1 a 5.

    Retorno:
        Preferência atualizada ou `None` para conta alheia/inexistente.

    Tratamento de erros:
        Nível fora do intervalo é rejeitado antes de alterar o modelo.
    """
    if not 1 <= nivel <= 5:
        raise ValueError("O nível de preferência deve estar entre 1 e 5.")
    preference = session.scalar(
        select(Preferencia).where(
            Preferencia.id == preferencia_id,
            Preferencia.usuario_id == usuario_id,
        )
    )
    if preference is None:
        return None
    preference.nivel = nivel
    session.flush()
    return preference
