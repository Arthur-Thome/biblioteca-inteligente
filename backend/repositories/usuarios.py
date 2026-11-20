"""Operações de persistência PostgreSQL para contas individuais."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models import Usuario
from backend.repositories._util import normalizar_texto


def criar_usuario(session: Session, *, nome: str, nome_usuario: str, senha_hash: str) -> Usuario:
    """Cria conta com nome de usuário canônico e senha já protegida.

    Parâmetros:
        session: sessão transacional provida por `session_scope`.
        nome: nome de exibição.
        nome_usuario: identificador que será normalizado para minúsculas.
        senha_hash: hash Werkzeug pré-calculado pelo módulo de autenticação.

    Retorno:
        Instância persistida de `Usuario`.

    Integração:
        O modelo aplica unicidade e valores canônicos no próprio PostgreSQL.

    Tratamento de erros:
        Entrada inválida produz `ValueError`; colisão é propagada como
        `IntegrityError` para a camada chamadora decidir a resposta.
    """
    display_name = normalizar_texto(nome, maximo=160, campo="Nome")
    username = normalizar_texto(nome_usuario, maximo=80, campo="Nome de usuário").casefold()
    password_hash = normalizar_texto(senha_hash, maximo=255, campo="Hash de senha")
    if not (password_hash.startswith("scrypt:") or password_hash.startswith("pbkdf2:")):
        raise ValueError("A senha deve chegar como hash Werkzeug, nunca em texto puro.")
    usuario = Usuario(nome=display_name, nome_usuario=username, senha_hash=password_hash)
    session.add(usuario)
    session.flush()
    return usuario


def obter_usuario(session: Session, usuario_id: UUID) -> Usuario | None:
    """Busca uma conta pela chave primária.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: identificador UUID da conta.

    Retorno:
        Conta encontrada ou `None` quando o identificador não existe.
    """
    return session.get(Usuario, usuario_id)


def obter_usuario_por_nome(session: Session, nome_usuario: str) -> Usuario | None:
    """Busca nome de usuário após aplicar a mesma normalização da criação.

    Parâmetros:
        session: sessão transacional ativa.
        nome_usuario: identificador textual informado pela camada chamadora.

    Retorno:
        Conta correspondente ou `None` quando não houver correspondência.
    """
    username = normalizar_texto(nome_usuario, maximo=80, campo="Nome de usuário").casefold()
    return session.scalar(select(Usuario).where(Usuario.nome_usuario == username))


def atualizar_perfil(session: Session, *, usuario_id: UUID, nome: str) -> Usuario | None:
    """Atualiza somente o nome de exibição da conta identificada.

    Parâmetros:
        session: sessão transacional ativa.
        usuario_id: proprietário do perfil a alterar.
        nome: novo nome de exibição.

    Retorno:
        Conta atualizada ou `None` quando ausente.
    """
    usuario = obter_usuario(session, usuario_id)
    if usuario is not None:
        usuario.nome = normalizar_texto(nome, maximo=160, campo="Nome")
        session.flush()
    return usuario
