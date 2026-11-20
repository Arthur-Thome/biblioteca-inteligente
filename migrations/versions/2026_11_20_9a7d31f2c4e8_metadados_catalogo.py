"""Adiciona metadados bibliográficos complementares sem alterar registros."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9a7d31f2c4e8"
down_revision = "887b2bb10d3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria coluna JSONB vazia para detalhes e origem dos metadados."""
    op.add_column(
        "livros",
        sa.Column(
            "metadados",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Remove somente o campo novo, sem alterar os demais dados bibliográficos."""
    op.drop_column("livros", "metadados")
