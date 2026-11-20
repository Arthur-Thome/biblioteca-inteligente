"""Cria e verifica o banco e a conta local da aplicação."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def load_local_settings() -> dict[str, str]:
    """Lê configurações locais sem mostrar os valores confidenciais.

    Retorno:
        Mapeamento das variáveis presentes no arquivo `.env`.

    Tratamento de erros:
        Arquivo ausente ou campos obrigatórios vazios interrompem a operação.
    """
    if not ENV_FILE.is_file():
        raise FileNotFoundError("O arquivo .env não existe; execute a preparação local.")
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    required = (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_ADMIN_USER",
        "POSTGRES_ADMIN_PASSWORD",
        "POSTGRES_APP_USER",
        "POSTGRES_APP_PASSWORD",
        "POSTGRES_DB",
    )
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError("Configuração local incompleta: " + ", ".join(missing))
    return values


def connect_admin(settings: dict[str, str]) -> psycopg.Connection:
    """Abre uma conexão administrativa somente à instância local do projeto.

    Parâmetros:
        settings: configurações locais lidas do arquivo ignorado pelo Git.

    Retorno:
        Conexão Psycopg autenticada no banco de manutenção.

    Integração:
        A conexão executa somente a criação inicial de role/banco ou consultas
        de verificação. A aplicação web não recebe esta credencial.

    Tratamento de erros:
        Falhas de autenticação, rede ou servidor são propagadas ao comando
        chamador sem incluir a senha em mensagens.
    """
    return psycopg.connect(
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        dbname="postgres",
        user=settings["POSTGRES_ADMIN_USER"],
        password=settings["POSTGRES_ADMIN_PASSWORD"],
        connect_timeout=5,
        sslmode="disable",
    )


def provision_database() -> None:
    """Cria a role de aplicação sem privilégios administrativos e o banco vazio.

    A operação é idempotente: roles e bancos existentes são verificados, nunca
    recriados nem redefinidos. Um proprietário inesperado gera erro para
    preservar dados e privilégios já existentes.
    """
    settings = load_local_settings()
    app_user = settings["POSTGRES_APP_USER"]
    database = settings["POSTGRES_DB"]
    admin_user = settings["POSTGRES_ADMIN_USER"]

    with connect_admin(settings) as connection:
        connection.autocommit = True
        role = connection.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolcanlogin "
            "FROM pg_roles WHERE rolname = %s",
            (app_user,),
        ).fetchone()
        if role is None:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(app_user),
                    sql.Literal(settings["POSTGRES_APP_PASSWORD"]),
                ),
            )
            role = (False, False, False, True)
        if role != (False, False, False, True):
            raise RuntimeError(
                "A conta de aplicação existente não atende ao perfil de menor privilégio."
            )

        owner = connection.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s",
            (database,),
        ).fetchone()
        if owner is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database), sql.Identifier(admin_user)
                )
            )
            owner = (admin_user,)
        elif owner[0] not in (app_user, admin_user):
            raise RuntimeError(
                "O banco já existe com outro proprietário; nenhuma alteração foi aplicada."
            )
        connection.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database), sql.Identifier(app_user)
            )
        )

    with psycopg.connect(
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        dbname=database,
        user=app_user,
        password=settings["POSTGRES_APP_PASSWORD"],
        connect_timeout=5,
        sslmode="disable",
    ) as connection:
        row = connection.execute(
            "SELECT current_user, current_database(), "
            "host(inet_server_addr()), r.rolsuper, r.rolcreatedb, r.rolcreaterole "
            "FROM pg_roles AS r WHERE r.rolname = current_user"
        ).fetchone()
        if row is None or row[2] != "127.0.0.1" or any(row[3:]):
            raise RuntimeError("A conexão ou os privilégios da conta não passaram na verificação.")
    print("Banco e conta de aplicação verificados com privilégios restritos.")


def provision_test_database() -> None:
    """Cria somente a base isolada de testes, sem limpar estruturas existentes.

    Integração:
        A conta administrativa cria a base com proprietário igual à role
        restrita da aplicação; a verificação posterior usa essa role.

    Tratamento de erros:
        Proprietário inesperado ou tabelas sem controle de migração interrompem
        a preparação sem remover dados existentes.
    """
    settings = load_local_settings()
    database = f"{settings['POSTGRES_DB']}_test"
    app_user = settings["POSTGRES_APP_USER"]
    admin_user = settings["POSTGRES_ADMIN_USER"]
    with connect_admin(settings) as connection:
        connection.autocommit = True
        owner = connection.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
            (database,),
        ).fetchone()
        if owner is None:
            connection.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database), sql.Identifier(admin_user)
                )
            )
            owner = (admin_user,)
        if owner[0] not in (app_user, admin_user):
            raise RuntimeError("A base de testes existente possui proprietário inesperado.")
        connection.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database), sql.Identifier(app_user)
            )
        )

    with psycopg.connect(
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        dbname=database,
        user=app_user,
        password=settings["POSTGRES_APP_PASSWORD"],
        connect_timeout=5,
        sslmode="disable",
    ) as connection:
        tables = connection.execute(
            "SELECT count(*) FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
        ).fetchone()[0]
        migration_table = connection.execute(
            "SELECT to_regclass('public.alembic_version')"
        ).fetchone()[0]
        if tables and migration_table is None:
            raise RuntimeError(
                "A base de testes possui tabelas sem controle de migração; "
                "nenhuma estrutura foi alterada."
            )
    print("Banco isolado de testes verificado; nenhuma tabela foi removida.")


def prepare_database_privileges() -> None:
    """Restringe DDL à conta administrativa e concede DML à aplicação.

    Integração:
        A role administrativa mantém propriedade do banco e das tabelas;
        `biblioteca_app` recebe conexão, uso do schema e DML nas tabelas.

    Tratamento de erros:
        Proprietários fora do conjunto conhecido ou bancos ausentes interrompem
        a configuração sem excluir nem recriar objetos.
    """
    settings = load_local_settings()
    admin = settings["POSTGRES_ADMIN_USER"]
    app_user = settings["POSTGRES_APP_USER"]
    databases = (settings["POSTGRES_DB"], f"{settings['POSTGRES_DB']}_test")
    with connect_admin(settings) as connection:
        connection.autocommit = True
        for database in databases:
            owner = connection.execute(
                "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
                (database,),
            ).fetchone()
            if owner is None:
                raise RuntimeError(f"O banco esperado {database} não existe.")
            if owner[0] == app_user:
                connection.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                        sql.Identifier(database), sql.Identifier(admin)
                    )
                )
            elif owner[0] != admin:
                raise RuntimeError(f"O banco {database} possui proprietário inesperado.")
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database), sql.Identifier(app_user)
                )
            )

    for database in databases:
        with psycopg.connect(
            host=settings["POSTGRES_HOST"],
            port=int(settings["POSTGRES_PORT"]),
            dbname=database,
            user=admin,
            password=settings["POSTGRES_ADMIN_PASSWORD"],
            connect_timeout=5,
            sslmode="disable",
        ) as connection:
            connection.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(app_user))
            )
            tables = connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
            for (table_name,) in tables:
                table_owner = connection.execute(
                    "SELECT pg_get_userbyid(relowner) FROM pg_class "
                    "WHERE oid=to_regclass(%s)",
                    (f'public."{table_name.replace(chr(34), chr(34) * 2)}"',),
                ).fetchone()
                if table_owner and table_owner[0] == app_user:
                    connection.execute(
                        sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(
                            sql.Identifier(table_name), sql.Identifier(admin)
                        )
                    )
                elif table_owner and table_owner[0] != admin:
                    raise RuntimeError(f"A tabela public.{table_name} possui proprietário inesperado.")
                connection.execute(
                    sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{} TO {}").format(
                        sql.Identifier(table_name), sql.Identifier(app_user)
                    )
                )
            connection.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(sql.Identifier(admin), sql.Identifier(app_user))
            )
            connection.commit()
    print("Privilégios preparados: migrations administrativas e DML restrito à aplicação.")


def verify_database() -> None:
    """Confirma autenticação administrativa e acesso restrito da aplicação.

    Retorno:
        Nenhum; os resultados seguros são informados sem exibir credenciais.
    """
    settings = load_local_settings()
    with connect_admin(settings) as connection:
        version, address, port, listen, encryption, data_directory = connection.execute(
            "SELECT current_setting('server_version'), host(inet_server_addr()), "
            "current_setting('port'), current_setting('listen_addresses'), "
            "current_setting('password_encryption'), "
            "current_setting('data_directory')"
        ).fetchone()
        expected_data = os.path.normcase(str((ROOT / "postgres" / "data").resolve()))
        actual_data = os.path.normcase(str(Path(data_directory).resolve()))
        scram = connection.execute(
            "SELECT bool_and(rolpassword LIKE 'SCRAM-SHA-256$%%') "
            "FROM pg_authid WHERE rolname = ANY(%s)",
            ([settings["POSTGRES_ADMIN_USER"], settings["POSTGRES_APP_USER"]],),
        ).fetchone()[0]
        if (
            not version.startswith("17.")
            or address != "127.0.0.1"
            or port != "5433"
            or listen != "127.0.0.1"
            or encryption != "scram-sha-256"
            or actual_data != expected_data
            or not scram
        ):
            raise RuntimeError("A instância não corresponde ao PostgreSQL 17 local esperado.")
    with psycopg.connect(
        host=settings["POSTGRES_HOST"],
        port=int(settings["POSTGRES_PORT"]),
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_APP_USER"],
        password=settings["POSTGRES_APP_PASSWORD"],
        connect_timeout=5,
        sslmode="disable",
    ) as connection:
        row = connection.execute(
            "SELECT current_user, current_database(), host(inet_server_addr()), "
            "r.rolsuper, r.rolcreatedb, r.rolcreaterole "
            "FROM pg_roles AS r WHERE r.rolname = current_user"
        ).fetchone()
        if (
            row is None
            or row[0] != settings["POSTGRES_APP_USER"]
            or row[1] != settings["POSTGRES_DB"]
            or row[2] != "127.0.0.1"
            or any(row[3:])
        ):
            raise RuntimeError("A conexão da aplicação ou seus privilégios são inesperados.")
    print(f"PostgreSQL {version}: autenticação administrativa e acesso restrito aprovados.")


def main() -> int:
    """Executa provisionamento explicitamente solicitado ou somente verificação."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true", help="cria recursos ausentes sem recriar dados")
    parser.add_argument("--setup-test-db", action="store_true", help="cria ou verifica somente a base isolada de testes")
    parser.add_argument("--prepare-privileges", action="store_true", help="separa propriedade administrativa e acesso DML")
    parser.add_argument("--check", action="store_true", help="executa somente verificações autenticadas")
    args = parser.parse_args()
    try:
        if args.setup:
            provision_database()
        if args.setup_test_db:
            provision_test_database()
        if args.prepare_privileges:
            prepare_database_privileges()
        verify_database()
    except psycopg.Error as error:
        print(f"Verificação PostgreSQL falhou: erro do driver {type(error).__name__}.")
        return 1
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Verificação PostgreSQL falhou: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
