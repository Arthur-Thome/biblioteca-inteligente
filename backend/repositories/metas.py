"""Operações de metas individuais associadas ao proprietário."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import BibliotecaUsuario, MetaLeitura, ProgressoLeitura


def criar_meta(
    session: Session,
    *,
    usuario_id: UUID,
    quantidade_objetivo: int,
    periodo_inicio: date,
    periodo_fim: date,
) -> MetaLeitura:
    """Cria meta com quantidade positiva e período crescente.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: conta proprietária da meta.
        quantidade_objetivo: livros a concluir no período.
        periodo_inicio, periodo_fim: datas inclusiva inicial e final.

    Retorno:
        Meta persistida; o progresso deve ser calculado a partir de leituras.

    Tratamento de erros:
        Quantidade ou datas inválidas geram `ValueError`; duplicação do mesmo
        período também é protegida por restrição única no PostgreSQL.
    """
    if quantidade_objetivo <= 0 or periodo_fim <= periodo_inicio:
        raise ValueError("A meta exige quantidade positiva e período crescente.")
    meta = MetaLeitura(
        usuario_id=usuario_id,
        quantidade_objetivo=quantidade_objetivo,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
    )
    session.add(meta)
    session.flush()
    return meta


def listar_metas(session: Session, *, usuario_id: UUID) -> list[MetaLeitura]:
    """Lista metas somente da conta solicitante, em ordem cronológica.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário obrigatório.

    Retorno:
        Lista de metas da conta.
    """
    return list(
        session.scalars(
            select(MetaLeitura)
            .where(MetaLeitura.usuario_id == usuario_id)
            .order_by(MetaLeitura.periodo_inicio)
        )
    )


def remover_meta(session: Session, *, usuario_id: UUID, meta_id: UUID) -> bool:
    """Remove meta com filtro simultâneo pelo UUID e usuário proprietário.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        meta_id: UUID da meta.

    Retorno:
        `True` se a meta própria foi removida; caso contrário, `False`.
    """
    meta = session.scalar(
        select(MetaLeitura).where(MetaLeitura.id == meta_id, MetaLeitura.usuario_id == usuario_id)
    )
    if meta is None:
        return False
    session.delete(meta)
    session.flush()
    return True


def atualizar_meta(
    session: Session,
    *,
    usuario_id: UUID,
    meta_id: UUID,
    quantidade_objetivo: int,
    periodo_inicio: date,
    periodo_fim: date,
) -> MetaLeitura | None:
    """Atualiza quantidade e período após validar a propriedade da meta.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        meta_id: UUID da meta a atualizar.
        quantidade_objetivo: nova quantidade positiva.
        periodo_inicio, periodo_fim: novo intervalo crescente.

    Retorno:
        Meta atualizada ou `None` quando não pertence ao proprietário.
    """
    meta = session.scalar(
        select(MetaLeitura).where(MetaLeitura.id == meta_id, MetaLeitura.usuario_id == usuario_id)
    )
    if meta is None:
        return None
    if quantidade_objetivo <= 0 or periodo_fim <= periodo_inicio:
        raise ValueError("A meta exige quantidade positiva e período crescente.")
    meta.quantidade_objetivo = quantidade_objetivo
    meta.periodo_inicio = periodo_inicio
    meta.periodo_fim = periodo_fim
    session.flush()
    return meta


def contar_livros_concluidos(
    session: Session, *, usuario_id: UUID, periodo_inicio: date, periodo_fim: date
) -> int:
    """Conta livros distintos concluídos dentro do período inclusivo da meta.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autenticado da coleção.
        periodo_inicio, periodo_fim: datas inclusivas de início e fim.

    Retorno:
        Quantidade de associações próprias atualmente com status concluído e
        data de conclusão dentro do período.

    Integração:
        A rota de metas combina essa contagem com MetaLeitura; a consulta usa
        a relação de biblioteca para excluir qualquer outra conta.

    Tratamento de erros:
        Os limites invertidos são rejeitados para evitar indicadores enganosos.
    """
    if periodo_fim < periodo_inicio:
        raise ValueError("O período final não pode anteceder o período inicial.")
    inicio = datetime.combine(periodo_inicio, time.min, tzinfo=timezone.utc)
    fim_exclusivo = datetime.combine(periodo_fim + timedelta(days=1), time.min, tzinfo=timezone.utc)
    total = session.scalar(
        select(func.count(func.distinct(ProgressoLeitura.biblioteca_usuario_id)))
        .join(BibliotecaUsuario, BibliotecaUsuario.id == ProgressoLeitura.biblioteca_usuario_id)
        .where(
            BibliotecaUsuario.usuario_id == usuario_id,
            ProgressoLeitura.status == "concluido",
            ProgressoLeitura.concluido_em >= inicio,
            ProgressoLeitura.concluido_em < fim_exclusivo,
        )
    )
    return int(total or 0)
