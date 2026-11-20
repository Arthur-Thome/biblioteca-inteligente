"""Reforça metadados ISBN e vetores bibliográficos em PostgreSQL."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '766b3c6df106'
down_revision: Union[str, None] = 'b86bc6695616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restringe formato de ISBN e listas bibliográficas na camada SQL."""
    op.create_check_constraint(
        "ck_livros_isbn_canonico",
        "livros",
        "isbn IS NULL OR (isbn = upper(btrim(isbn)) AND isbn ~ '^(?:[0-9]{9}[0-9X]|[0-9]{13})$')",
    )
    op.create_check_constraint("ck_livros_autores_array", "livros", "jsonb_typeof(autores) = 'array'")
    op.create_check_constraint("ck_livros_generos_array", "livros", "jsonb_typeof(generos) = 'array'")
    op.create_check_constraint("ck_livros_assuntos_array", "livros", "jsonb_typeof(assuntos) = 'array'")


def downgrade() -> None:
    """Remove somente as quatro verificações da revisão selecionada."""
    op.drop_constraint("ck_livros_assuntos_array", "livros", type_="check")
    op.drop_constraint("ck_livros_generos_array", "livros", type_="check")
    op.drop_constraint("ck_livros_autores_array", "livros", type_="check")
    op.drop_constraint("ck_livros_isbn_canonico", "livros", type_="check")
