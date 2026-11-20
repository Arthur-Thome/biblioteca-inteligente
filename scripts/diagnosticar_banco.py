"""Exibe um inventário não confidencial do banco local do projeto."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from psycopg import sql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configurar_postgres import connect_admin, load_local_settings
from backend.database import create_database_engine
from backend.models import Base
from sqlalchemy import text


def main() -> int:
    """Consulta estrutura e propriedade sem alterar o banco.

    Retorno:
        Código zero quando o inventário somente leitura é concluído.

    Integração:
        Utiliza a conexão administrativa existente apenas para metadados e
        confirma a visibilidade das tabelas pela conta de aplicação.

    Tratamento de erros:
        Erros de configuração e conexão são relatados sem imprimir credenciais.
    """
    settings = load_local_settings()
    with connect_admin(settings) as connection:
        owner = connection.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
            (settings["POSTGRES_DB"],),
        ).fetchone()
    with psycopg.connect(
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_ADMIN_USER"],
        password=settings["POSTGRES_ADMIN_PASSWORD"],
        sslmode="disable",
    ) as connection:
        tables = connection.execute(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY schemaname, tablename"
        ).fetchall()
        print(f"Proprietário do banco: {owner[0] if owner else 'ausente'}")
        print(f"Tabelas existentes: {len(tables)}")
        for schema, table in tables:
            print(f"  {schema}.{table}")
        for table in Base.metadata.sorted_tables:
            count = connection.execute(
                sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table.name))
            ).fetchone()[0]
            print(f"  Registros em {table.name}: {count}")

    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            user, database, can_create = connection.execute(
                text(
                    "SELECT current_user, current_database(), "
                    "has_schema_privilege(current_user, 'public', 'CREATE')"
                )
            ).one()
            visible_tables = connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalar_one()
            print(f"Conta de runtime autenticada: {user} em {database}")
            print(f"Permissão de criar objetos de esquema: {'sim' if can_create else 'não'}")
            print(f"Tabelas visíveis à aplicação: {visible_tables}")
    finally:
        engine.dispose()

    print("Inventário concluído sem alterações.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
