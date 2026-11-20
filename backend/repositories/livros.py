"""Consultas e gravações de registros bibliográficos compartilháveis."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Livro
from backend.repositories._util import normalizar_isbn, normalizar_texto


def obter_por_catalogo(session: Session, *, origem: str, identificador: str) -> Livro | None:
    """Busca um registro pela chave estável devolvida pelo catálogo externo.

    Parâmetros:
        session: sessão transacional ativa.
        origem: nome normalizado do catálogo bibliográfico.
        identificador: chave de obra ou edição fornecida pelo serviço.

    Retorno:
        Livro existente ou `None` quando o registro ainda não foi cadastrado.
    """
    return session.scalar(select(Livro).where(
        Livro.origem_catalogo == origem.casefold(),
        Livro.identificador_externo == identificador.strip(),
    ))


def criar_livro(
    session: Session,
    *,
    titulo: str,
    autores: list[str] | None = None,
    descricao: str | None = None,
    isbn: str | None = None,
    identificador_externo: str | None = None,
    origem_catalogo: str | None = None,
    url_capa: str | None = None,
    ano_publicacao: int | None = None,
    generos: list[str] | None = None,
    assuntos: list[str] | None = None,
    metadados: dict | None = None,
) -> Livro:
    """Persiste registro de obra ou edição sem deduplicar apenas por título.

    Parâmetros:
        session: sessão transacional ativa.
        titulo: título bibliográfico obrigatório.
        autores, generos, assuntos: listas de metadados conservadas em JSONB.
        descricao, isbn, identificador_externo, origem_catalogo, url_capa,
        ano_publicacao: campos opcionais da edição.
        metadados: informações complementares e proveniência por campo.

    Retorno:
        Livro persistido com identificador UUID.

    Integração:
        Índices parciais do modelo evitam repetir identificadores de catálogo e
        ISBN sem exigir título único.

    Tratamento de erros:
        Campos inválidos geram `ValueError`; colisões únicas são propagadas
        como erro de integridade do PostgreSQL.
    """
    if (
        not isinstance(autores or [], list)
        or not isinstance(generos or [], list)
        or not isinstance(assuntos or [], list)
    ):
        raise ValueError("Autores, gêneros e assuntos devem ser listas de texto.")
    for values in (autores or [], generos or [], assuntos or []):
        if any(not isinstance(value, str) for value in values):
            raise ValueError("Os metadados bibliográficos devem conter somente texto.")
    if ano_publicacao is not None and not 0 <= ano_publicacao <= 9999:
        raise ValueError("Ano de publicação fora do intervalo permitido.")
    if metadados is not None and not isinstance(metadados, dict):
        raise ValueError("Os metadados complementares devem formar um objeto JSON.")
    isbn_clean = normalizar_isbn(isbn)
    external = identificador_externo.strip() if identificador_externo else None
    source = origem_catalogo.strip().casefold() if origem_catalogo else None
    if bool(external) != bool(source):
        raise ValueError("Origem e identificador externo devem ser informados juntos.")
    livro = Livro(
        titulo=normalizar_texto(titulo, maximo=500, campo="Título"),
        autores=autores or [],
        descricao=descricao.strip() if descricao else None,
        isbn=isbn_clean,
        identificador_externo=external,
        origem_catalogo=source,
        url_capa=url_capa.strip() if url_capa else None,
        ano_publicacao=ano_publicacao,
        generos=generos or [],
        assuntos=assuntos or [],
        metadados=metadados or {},
    )
    session.add(livro)
    session.flush()
    return livro


def obter_livro(session: Session, livro_id: UUID) -> Livro | None:
    """Busca um registro bibliográfico pelo UUID.

    Parâmetros:
        session: sessão transacional ativa.
        livro_id: chave primária do registro.

    Retorno:
        Livro encontrado ou `None`.
    """
    return session.get(Livro, livro_id)


def pesquisar_livros(session: Session, *, titulo: str, limite: int = 50, deslocamento: int = 0) -> list[Livro]:
    """Pesquisa título com filtro parametrizado e paginação limitada.

    Parâmetros:
        session: sessão transacional ativa.
        titulo: trecho de título pesquisado sem interpolação SQL.
        limite: máximo de resultados, limitado a 100.
        deslocamento: número de resultados anteriores a ignorar.

    Retorno:
        Lista ordenada de registros correspondentes.
    """
    if not 1 <= limite <= 100 or deslocamento < 0:
        raise ValueError("A paginação deve usar limite de 1 a 100 e deslocamento não negativo.")
    term = normalizar_texto(titulo, maximo=500, campo="Título de pesquisa")
    statement = (
        select(Livro)
        .where(Livro.titulo.ilike(f"%{term}%"))
        .order_by(Livro.titulo)
        .limit(limite)
        .offset(deslocamento)
    )
    return list(session.scalars(statement))


def atualizar_livro(session: Session, *, livro_id: UUID, titulo: str, descricao: str | None) -> Livro | None:
    """Atualiza os campos editoriais comuns sem alterar identificadores.

    Parâmetros:
        session: sessão transacional ativa.
        livro_id: edição bibliográfica a alterar.
        titulo: novo título obrigatório.
        descricao: nova descrição opcional.

    Retorno:
        Livro atualizado ou `None` quando ausente.
    """
    livro = obter_livro(session, livro_id)
    if livro is None:
        return None
    livro.titulo = normalizar_texto(titulo, maximo=500, campo="Título")
    livro.descricao = descricao.strip() if descricao else None
    session.flush()
    return livro


def remover_livro_sem_associacoes(session: Session, *, livro_id: UUID) -> bool:
    """Remove registro bibliográfico somente se não houver bibliotecas ligadas.

    Parâmetros:
        session: sessão transacional ativa.
        livro_id: edição candidata à remoção.

    Retorno:
        `True` quando a remoção segura ocorreu; `False` quando não existe.

    Tratamento de erros:
        O PostgreSQL rejeita a remoção quando há associações; o RESTRICT
        preserva histórico e referências de outras pessoas.
    """
    livro = obter_livro(session, livro_id)
    if livro is None:
        return False
    session.delete(livro)
    session.flush()
    return True
