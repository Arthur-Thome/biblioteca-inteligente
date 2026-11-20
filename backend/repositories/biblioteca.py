"""Acesso às associações de livros sempre escopado pelo proprietário."""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy import Text, cast, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.models import BibliotecaUsuario, Livro, ProgressoLeitura

_ACCENT_SOURCE = "áàãâäéèêëíìîïóòõôöúùûüç"
_ACCENT_TARGET = "aaaaaeeeeiiiiooooouuuuc"


def _normalizar_consulta(value: str) -> str:
    """Normaliza entrada de pesquisa para comparação sem diferença de acento.

    Parâmetros:
        value: texto de busca recebido e previamente validado pela rota.

    Retorno:
        Texto Unicode em minúsculas, sem diacríticos e com espaços reduzidos.

    Integração:
        A normalização é usada apenas na consulta pessoal da biblioteca.

    Tratamento de erros:
        Entradas não textuais são rejeitadas pelo endpoint antes desta função.
    """
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def _texto_sem_acento(expression):
    """Gera expressão SQL parametrizada que aproxima texto sem diacríticos.

    Parâmetros:
        expression: expressão SQLAlchemy textual, nunca SQL recebido do cliente.

    Retorno:
        Expressão `translate(lower(...))` executada pelo PostgreSQL.

    Integração:
        Repositório aplica a expressão a título, autores, assuntos e ISBN.
    """
    return func.translate(func.lower(expression), _ACCENT_SOURCE, _ACCENT_TARGET)


def _padrao_literal(value: str) -> str:
    """Escapa curingas LIKE para que termos sejam tratados como texto literal.

    Parâmetros:
        value: trecho já normalizado da pesquisa ou filtro pessoal.

    Retorno:
        Padrão SQL LIKE delimitado por curingas e com caracteres escapados.

    Integração:
        O chamador entrega o padrão como parâmetro vinculado do SQLAlchemy.

    Tratamento de erros:
        A função não executa SQL nem interpreta a entrada como comando.
    """
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def adicionar_livro(session: Session, *, usuario_id: UUID, livro_id: UUID) -> BibliotecaUsuario:
    """Associa livro existente ao usuário sem criar duplicata na coleção.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário informado pela sessão autenticada da aplicação.
        livro_id: registro bibliográfico compartilhado.

    Retorno:
        Associação existente ou recém-criada.

    Tratamento de erros:
        UUID inexistente produz `ValueError`; corrida de unicidade recupera a
        associação já criada quando ela puder ser consultada na mesma conta.
    """
    existing = session.scalar(
        select(BibliotecaUsuario).where(
            BibliotecaUsuario.usuario_id == usuario_id,
            BibliotecaUsuario.livro_id == livro_id,
        )
    )
    if existing is not None:
        return existing
    if session.get(Livro, livro_id) is None:
        raise ValueError("O livro informado não existe.")
    item = BibliotecaUsuario(usuario_id=usuario_id, livro_id=livro_id)
    try:
        with session.begin_nested():
            session.add(item)
            session.flush()
        return item
    except IntegrityError:
        existing = session.scalar(
            select(BibliotecaUsuario).where(
                BibliotecaUsuario.usuario_id == usuario_id,
                BibliotecaUsuario.livro_id == livro_id,
            )
        )
        if existing is not None:
            return existing
        raise


def listar_livros_usuario(
    session: Session, *, usuario_id: UUID, limite: int = 100, deslocamento: int = 0
) -> list[BibliotecaUsuario]:
    """Lista associações e metadados somente para a conta solicitante.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário obrigatório para isolamento entre contas.
        limite: quantidade máxima de associações, limitada a 200.
        deslocamento: posição inicial da paginação.

    Retorno:
        Associações da conta com os livros carregados.
    """
    if not 1 <= limite <= 200 or deslocamento < 0:
        raise ValueError("A paginação deve usar limite de 1 a 200 e deslocamento não negativo.")
    statement = (
        select(BibliotecaUsuario)
        .options(joinedload(BibliotecaUsuario.livro))
        .where(BibliotecaUsuario.usuario_id == usuario_id)
        .order_by(BibliotecaUsuario.adicionado_em.desc())
        .limit(limite)
        .offset(deslocamento)
    )
    return list(session.scalars(statement))


def listar_pagina_usuario(
    session: Session,
    *,
    usuario_id: UUID,
    consulta: str = "",
    autor: str = "",
    assunto: str = "",
    favoritos: bool = False,
    ordenacao: str = "adicionados_recentes",
    pagina: int = 1,
    tamanho: int = 12,
) -> dict[str, object]:
    """Pesquisa e pagina a coleção sem carregar livros de outras contas.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário obtido exclusivamente da sessão autenticada.
        consulta, autor, assunto: filtros textuais sem distinção de caixa/acento.
        favoritos: restringe o resultado aos itens marcados como favoritos.
        ordenacao: chave selecionada entre as ordenações permitidas pelo domínio.
        pagina: página iniciada em um.
        tamanho: quantidade por página, limitada a 48.

    Retorno:
        Dicionário com associações da página, total filtrado e resumos da conta.

    Integração:
        A rota Flask serializa o resultado como JSON para renderização no site.

    Tratamento de erros:
        Página, tamanho ou ordenação fora dos limites geram `ValueError`.
    """
    if pagina < 1 or not 1 <= tamanho <= 48:
        raise ValueError("A página ou o tamanho solicitado está fora do intervalo permitido.")
    ordering = {
        "titulo_asc": (func.lower(Livro.titulo).asc(), BibliotecaUsuario.id.asc()),
        "titulo_desc": (func.lower(Livro.titulo).desc(), BibliotecaUsuario.id.asc()),
        "autor_asc": (func.lower(cast(Livro.autores, Text)).asc(), Livro.titulo.asc(), BibliotecaUsuario.id.asc()),
        "adicionados_recentes": (BibliotecaUsuario.adicionado_em.desc(), BibliotecaUsuario.id.desc()),
        "adicionados_antigos": (BibliotecaUsuario.adicionado_em.asc(), BibliotecaUsuario.id.asc()),
    }
    if ordenacao not in ordering:
        raise ValueError("A ordenação solicitada não é permitida.")

    owner_scope = BibliotecaUsuario.usuario_id == usuario_id
    conditions = [owner_scope]
    if consulta:
        term = _normalizar_consulta(consulta)
        pattern = _padrao_literal(term)
        isbn_term = re.sub(r"[^0-9Xx]", "", consulta).upper()
        isbn_pattern = _padrao_literal(isbn_term) if len(isbn_term) in {10, 13} else pattern
        conditions.append(or_(
            _texto_sem_acento(Livro.titulo).ilike(pattern, escape="\\"),
            _texto_sem_acento(cast(Livro.autores, Text)).ilike(pattern, escape="\\"),
            _texto_sem_acento(func.coalesce(Livro.isbn, "")).ilike(isbn_pattern, escape="\\"),
            _texto_sem_acento(cast(Livro.metadados, Text)).ilike(isbn_pattern, escape="\\"),
        ))
    if autor:
        conditions.append(_texto_sem_acento(cast(Livro.autores, Text)).ilike(
            _padrao_literal(_normalizar_consulta(autor)), escape="\\"
        ))
    if assunto:
        conditions.append(_texto_sem_acento(cast(Livro.assuntos, Text)).ilike(
            _padrao_literal(_normalizar_consulta(assunto)), escape="\\"
        ))
    if favoritos:
        conditions.append(BibliotecaUsuario.favorito.is_(True))

    base = select(BibliotecaUsuario).join(BibliotecaUsuario.livro).where(*conditions)
    filtered_total = session.scalar(
        select(func.count(BibliotecaUsuario.id)).join(BibliotecaUsuario.livro).where(*conditions)
    ) or 0
    total_books = session.scalar(
        select(func.count(BibliotecaUsuario.id)).where(owner_scope)
    ) or 0
    total_favorites = session.scalar(
        select(func.count(BibliotecaUsuario.id)).where(
            owner_scope, BibliotecaUsuario.favorito.is_(True)
        )
    ) or 0
    entries = list(session.scalars(
        base.options(
            joinedload(BibliotecaUsuario.livro),
            joinedload(BibliotecaUsuario.progresso),
        )
        .order_by(*ordering[ordenacao])
        .limit(tamanho)
        .offset((pagina - 1) * tamanho)
    ))
    return {
        "entries": entries,
        "filtered_total": int(filtered_total),
        "total_books": int(total_books),
        "total_favorites": int(total_favorites),
    }


def atualizar_dados_pessoais(
    session: Session,
    *,
    usuario_id: UUID,
    item_id: UUID,
    favorito: bool | None = None,
    observacoes_pessoais: str | None = None,
    atualizar_observacoes: bool = False,
) -> BibliotecaUsuario | None:
    """Atualiza favorito e/ou observação somente na associação do proprietário.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autenticado.
        item_id: UUID da associação pessoal, não do livro compartilhado.
        favorito: estado booleano opcional para atualização.
        observacoes_pessoais: texto pessoal opcional.
        atualizar_observacoes: distingue ausência de campo de valor nulo.

    Retorno:
        Associação atualizada ou `None` quando não pertence à conta.

    Integração:
        As rotas PATCH validam CSRF e payload antes de chamar o repositório.

    Tratamento de erros:
        O banco protege o limite de 2.000 caracteres e erros transacionais
        são propagados para a camada HTTP.
    """
    item = obter_item_usuario(session, usuario_id=usuario_id, item_id=item_id)
    if item is None:
        return None
    if favorito is not None:
        item.favorito = favorito
    if atualizar_observacoes:
        item.observacoes_pessoais = observacoes_pessoais
    session.flush()
    return item


def obter_item_usuario(session: Session, *, usuario_id: UUID, item_id: UUID) -> BibliotecaUsuario | None:
    """Busca associação por identificador e proprietário em uma única consulta.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário autorizado.
        item_id: UUID da associação a consultar.

    Retorno:
        Associação pertencente à conta, ou `None` para qualquer outro dono.
    """
    return session.scalar(
        select(BibliotecaUsuario)
        .options(joinedload(BibliotecaUsuario.livro), joinedload(BibliotecaUsuario.progresso))
        .where(
            BibliotecaUsuario.id == item_id,
            BibliotecaUsuario.usuario_id == usuario_id,
        )
    )


def remover_livro_usuario(session: Session, *, usuario_id: UUID, item_id: UUID) -> bool:
    """Remove apenas a associação do dono e seu progresso, sem apagar o livro.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário usado para restringir a exclusão.
        item_id: UUID da associação pessoal.

    Retorno:
        `True` quando uma associação própria foi removida; caso contrário,
        `False`. O chamador confirma a transação no fechamento da sessão.
    """
    item = obter_item_usuario(session, usuario_id=usuario_id, item_id=item_id)
    if item is None:
        return False
    # A exclusão explícita preserva o RESTRICT e evita cascata do histórico.
    session.execute(
        delete(ProgressoLeitura).where(ProgressoLeitura.biblioteca_usuario_id == item.id),
        execution_options={"synchronize_session": "fetch"},
    )
    session.flush()
    session.delete(item)
    session.flush()
    return True
