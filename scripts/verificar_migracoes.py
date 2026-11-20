"""Compara a revisão Alembic aplicada com o head local sem alterar dados."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from backend.database import get_database_url


def main() -> int:
    """Confirma que o banco principal está na revisão Alembic mais recente.

    Retorno:
        Zero quando revisão aplicada e head local coincidem; um nos demais
        casos, sem imprimir credenciais nem exceções internas.

    Integração:
        Usa a configuração Alembic local e URL administrativa validada.
    """
    engine = create_engine(get_database_url(administrative=True), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
        configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
        configuration.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
        head = ScriptDirectory.from_config(configuration).get_current_head()
    except Exception as error:
        print(f"Verificação de migrações indisponível: {type(error).__name__}.")
        return 1
    finally:
        engine.dispose()
    if current is None:
        print("Nenhuma revisão foi aplicada.")
        return 1
    if current != head:
        print("A revisão PostgreSQL está desatualizada em relação aos arquivos locais.")
        return 1
    print(f"Revisão PostgreSQL atual: {current} (head).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
