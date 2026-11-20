"""Ambiente de execução das migrações versionadas Alembic."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from backend.database import get_database_url
from backend.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera SQL sem abrir conexão e direciona ao banco configurado.

    Integração:
        O modo offline usa o mesmo URL validado do módulo de banco e os
        metadados dos modelos para comparar o esquema desejado.
    """
    context.configure(
        url=get_database_url(administrative=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações em conexão transacional ao destino local validado.

    Integração:
        SQLAlchemy cria a conexão que Alembic usa para registrar a revisão e
        aplicar operações versionadas no PostgreSQL.

    Tratamento de erros:
        Falhas propagam ao comando Alembic; o engine é encerrado no bloco final.
    """
    engine = create_engine(get_database_url(administrative=True), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
