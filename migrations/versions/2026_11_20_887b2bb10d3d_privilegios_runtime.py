"""Concede DML à aplicação sem liberar criação de objetos de esquema."""

from __future__ import annotations

from alembic import op

from backend.database import load_database_settings

revision: str = "887b2bb10d3d"
down_revision: str | None = "766b3c6df106"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Permite operações de dados e define privilégios padrão do runtime.

    Integração:
        Alembic executa esta revisão com a role administrativa, enquanto o
        nome da conta de runtime vem da configuração local protegida.
    """
    settings = load_database_settings()
    bind = op.get_bind()
    quote = bind.dialect.identifier_preparer.quote
    app_role = quote(settings["POSTGRES_APP_USER"])
    admin_role = quote(settings["POSTGRES_ADMIN_USER"])
    bind.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {app_role}")
    bind.exec_driver_sql(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_role}"
    )
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{admin_role} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role}"
    )


def downgrade() -> None:
    """Revoga privilégios DML sem remover tabelas nem dados existentes."""
    settings = load_database_settings()
    bind = op.get_bind()
    quote = bind.dialect.identifier_preparer.quote
    app_role = quote(settings["POSTGRES_APP_USER"])
    admin_role = quote(settings["POSTGRES_ADMIN_USER"])
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{admin_role} IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {app_role}"
    )
    bind.exec_driver_sql(
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {app_role}"
    )
