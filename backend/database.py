"""Configuração segura do acesso SQLAlchemy ao PostgreSQL local."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def load_database_settings() -> dict[str, str]:
    """Lê parâmetros PostgreSQL sem exibir credenciais locais.

    Retorno:
        Mapeamento com host, porta, usuários, senhas e nome do banco.

    Integração:
        O módulo usa o mesmo arquivo `.env` protegido pelos scripts locais.

    Tratamento de erros:
        Arquivo ou parâmetros obrigatórios ausentes geram `RuntimeError`.
    """
    if not ENV_FILE.is_file():
        raise RuntimeError("A configuração local .env não foi encontrada.")
    settings: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD", "POSTGRES_DB"):
        if not settings.get(key):
            raise RuntimeError(f"A configuração local não possui o campo {key}.")
    for key in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD", "POSTGRES_DB"):
        if os.environ.get(key):
            settings[key] = os.environ[key]
    if settings["POSTGRES_HOST"] != "127.0.0.1":
        raise RuntimeError("A conexão PostgreSQL aceita somente o host local 127.0.0.1.")
    try:
        port = int(settings["POSTGRES_PORT"])
    except ValueError as error:
        raise RuntimeError("A porta PostgreSQL local é inválida.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("A porta PostgreSQL local está fora do intervalo permitido.")
    settings = {
        key: settings[key]
        for key in (
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_ADMIN_USER",
            "POSTGRES_ADMIN_PASSWORD",
            "POSTGRES_APP_USER",
            "POSTGRES_APP_PASSWORD",
            "POSTGRES_DB",
        )
        if key in settings
    }
    return settings


def get_database_url(database_name: str | None = None, *, administrative: bool = False) -> URL:
    """Monta URL Psycopg sem interpolar credenciais em texto SQL.

    Parâmetros:
        database_name: banco principal ou base isolada terminada em `_test`.
        administrative: seleciona credencial administrativa somente para
            migrações e preparação de privilégios.

    Retorno:
        URL SQLAlchemy com driver `postgresql+psycopg`.

    Integração:
        A URL é consumida pelo engine, Alembic e repositórios.

    Tratamento de erros:
        Nome de banco fora dos dois destinos permitidos é rejeitado.
    """
    settings = load_database_settings()
    selected_database = database_name or os.environ.get("BIBLIOTECA_DATABASE_NAME") or settings["POSTGRES_DB"]
    allowed = {settings["POSTGRES_DB"], f"{settings['POSTGRES_DB']}_test"}
    if selected_database not in allowed:
        raise RuntimeError("O destino PostgreSQL não corresponde ao banco local ou à base de testes permitida.")
    if administrative:
        username = settings.get("POSTGRES_ADMIN_USER", "")
        password = settings.get("POSTGRES_ADMIN_PASSWORD", "")
        if not username or not password:
            raise RuntimeError("A configuração administrativa local está incompleta.")
    else:
        username = settings["POSTGRES_APP_USER"]
        password = settings["POSTGRES_APP_PASSWORD"]
    return URL.create(
        "postgresql+psycopg",
        username=username,
        password=password,
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        database=selected_database,
        query={"sslmode": "disable"},
    )


def create_database_engine(database_name: str | None = None) -> Engine:
    """Cria engine PostgreSQL com verificação da conexão reutilizada.

    Parâmetros:
        database_name: destino local permitido; o principal é o padrão.

    Retorno:
        Engine SQLAlchemy; o chamador deve executar `dispose()` ao encerrar.

    Integração:
        O engine alimenta sessões transacionais e ferramentas de migração.

    Tratamento de erros:
        Erros de conexão são propagados sem conteúdo de credenciais.
    """
    return create_engine(get_database_url(database_name), pool_pre_ping=True)


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """Fornece sessão transacional e garante rollback/fechamento.

    Parâmetros:
        engine: engine existente para compartilhamento ou engine local novo.

    Retorno:
        Contexto iterável com uma `Session` SQLAlchemy.

    Integração:
        Repositórios executam operações dentro deste contexto; sucesso confirma
        a transação e uma exceção reverte as alterações.

    Tratamento de erros:
        A exceção original é propagada depois do rollback e do fechamento.
    """
    owns_engine = engine is None
    active_engine = engine or create_database_engine()
    factory = sessionmaker(bind=active_engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        if owns_engine:
            active_engine.dispose()
