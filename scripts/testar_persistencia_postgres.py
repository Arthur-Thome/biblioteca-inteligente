"""Confere gravação durável exclusivamente na base local de testes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import create_database_engine, session_scope
from backend.models import Livro, Usuario
from backend.repositories import biblioteca, livros, usuarios

TEST_DATABASE = "biblioteca_inteligente_test"
MARKER_PATTERN = re.compile(r"^probe_[0-9a-f]{24}$")


def create_probe() -> str:
    """Grava usuário e livro descartáveis e retorna identificador não secreto.

    Retorno:
        Nome de usuário temporário usado para a leitura após reinício.

    Integração:
        Repositórios gravam no banco de teste usando uma transação confirmada.
    """
    marker = f"probe_{uuid4().hex[:24]}"
    engine = create_database_engine(TEST_DATABASE)
    try:
        with session_scope(engine) as session:
            account = usuarios.criar_usuario(
                session,
                nome="Registro temporário de persistência",
                nome_usuario=marker,
                senha_hash=generate_password_hash("credencial-descartavel"),
            )
            book = livros.criar_livro(session, titulo=f"Livro temporário {marker}")
            biblioteca.adicionar_livro(session, usuario_id=account.id, livro_id=book.id)
    finally:
        engine.dispose()
    return marker


def verify_probe(marker: str) -> bool:
    """Consulta os dados confirmados por conexão nova após reinicialização.

    Parâmetros:
        marker: nome temporário validado pelo formato local da prova.

    Retorno:
        `True` quando conta, livro e associação continuam disponíveis.
    """
    engine = create_database_engine(TEST_DATABASE)
    try:
        with session_scope(engine) as session:
            account = usuarios.obter_usuario_por_nome(session, marker)
            if account is None:
                return False
            items = biblioteca.listar_livros_usuario(session, usuario_id=account.id)
            return len(items) == 1 and items[0].livro.titulo == f"Livro temporário {marker}"
    finally:
        engine.dispose()


def cleanup_probe(marker: str) -> None:
    """Remove somente os registros com marcador exclusivo desta prova.

    Parâmetros:
        marker: nome temporário validado antes de qualquer exclusão.

    Tratamento de erros:
        Marcador fora do formato esperado é rejeitado sem consulta ou alteração.
    """
    if not MARKER_PATTERN.fullmatch(marker):
        raise ValueError("O identificador não corresponde à prova temporária.")
    engine = create_database_engine(TEST_DATABASE)
    try:
        with session_scope(engine) as session:
            account = usuarios.obter_usuario_por_nome(session, marker)
            if account is None:
                return
            items = biblioteca.listar_livros_usuario(session, usuario_id=account.id)
            book_ids = [item.livro_id for item in items]
            for item in items:
                biblioteca.remover_livro_usuario(
                    session, usuario_id=account.id, item_id=item.id
                )
            session.delete(account)
            session.flush()
            for book_id in book_ids:
                book = session.get(Livro, book_id)
                if book is not None and not session.scalar(
                    select(Livro.id).where(Livro.id == book_id, Livro.itens_biblioteca.any())
                ):
                    session.delete(book)
    finally:
        engine.dispose()


def main() -> int:
    """Executa uma única fase escolhida da prova de persistência isolada."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--criar", action="store_true", help="grava marcador descartável na base _test")
    group.add_argument("--verificar", metavar="MARCADOR", help="confere marcador após reinicialização")
    group.add_argument("--limpar", metavar="MARCADOR", help="remove somente os registros da prova")
    arguments = parser.parse_args()
    if arguments.criar:
        print(create_probe())
        return 0
    marker = arguments.verificar or arguments.limpar
    if not MARKER_PATTERN.fullmatch(marker):
        parser.error("o marcador deve seguir o formato probe_ e 24 dígitos hexadecimais")
    if arguments.verificar:
        if not verify_probe(marker):
            print("Falha: os registros de teste não foram encontrados após a reinicialização.")
            return 1
        print("Conta, livro e associação persistiram após reinicialização do PostgreSQL.")
        return 0
    cleanup_probe(marker)
    print("Registros temporários da prova foram removidos somente da base de testes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
