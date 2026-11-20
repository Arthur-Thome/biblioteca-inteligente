"""Operações de progresso vinculadas a uma associação pessoal."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import BibliotecaUsuario, ProgressoLeitura
from backend.repositories.biblioteca import obter_item_usuario

STATUS_VALIDOS = {"nao_iniciado", "lendo", "concluido", "abandonado"}


def salvar_progresso(
    session: Session,
    *,
    usuario_id: UUID,
    item_id: UUID,
    status: str,
    paginas_lidas: int = 0,
    total_paginas: int | None = None,
    iniciado_em: datetime | None = None,
    concluido_em: datetime | None = None,
    observacoes: str | None = None,
) -> ProgressoLeitura:
    """Cria ou atualiza progresso após validar proprietário e limites.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: dono da associação e autorização lógica da operação.
        item_id: associação pessoal cujo progresso é alterado.
        status: um dos quatro estados documentados no modelo.
        paginas_lidas, total_paginas: contagens não negativas e consistentes.
        iniciado_em, concluido_em: timestamps opcionais com fuso horário.
        observacoes: anotação opcional.

    Retorno:
        Progresso persistido para a associação do proprietário.

    Tratamento de erros:
        Dono ausente ou estado inválido produz `ValueError`; as restrições SQL
        também impedem páginas incompatíveis em operações diretas.
    """
    if obter_item_usuario(session, usuario_id=usuario_id, item_id=item_id) is None:
        raise ValueError("A associação não existe para o usuário informado.")
    if status not in STATUS_VALIDOS:
        raise ValueError("Status de leitura inválido.")
    if paginas_lidas < 0 or (total_paginas is not None and total_paginas < 1):
        raise ValueError("A quantidade de páginas informada é inválida.")
    if total_paginas is not None and paginas_lidas > total_paginas:
        raise ValueError("Páginas lidas não podem exceder o total conhecido.")
    if iniciado_em and concluido_em and concluido_em < iniciado_em:
        raise ValueError("A conclusão não pode anteceder o início da leitura.")
    item = session.get(BibliotecaUsuario, item_id)
    if item is None:
        raise ValueError("A associação pessoal não está mais disponível.")
    record = session.scalar(
        select(ProgressoLeitura).where(ProgressoLeitura.biblioteca_usuario_id == item.id)
    )
    if record is None:
        record = ProgressoLeitura(biblioteca_usuario_id=item.id)
        session.add(record)
    record.status = status
    record.paginas_lidas = paginas_lidas
    record.total_paginas = total_paginas
    record.iniciado_em = iniciado_em
    record.concluido_em = concluido_em
    record.observacoes = observacoes.strip() if observacoes else None
    session.flush()
    return record


def obter_progresso(session: Session, *, usuario_id: UUID, item_id: UUID) -> ProgressoLeitura | None:
    """Consulta progresso após confirmar que a associação pertence à conta.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        item_id: UUID da associação pessoal.

    Retorno:
        Progresso associado ou `None` se não existir ou não pertencer ao dono.
    """
    if obter_item_usuario(session, usuario_id=usuario_id, item_id=item_id) is None:
        return None
    return session.scalar(
        select(ProgressoLeitura).where(ProgressoLeitura.biblioteca_usuario_id == item_id)
    )
