"""Adiciona campos pessoais e índice de favoritos à associação da biblioteca."""

from alembic import op
import sqlalchemy as sa

revision = "c4e8a19f07d2"
down_revision = "9a7d31f2c4e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Cria favorito e observações sem alterar livros ou associações existentes.

    Retorno:
        Nenhum valor; o PostgreSQL preenche associações existentes com falso.

    Integração:
        Os campos pertencem à tabela associativa e são consumidos pelo
        repositório de biblioteca, que sempre exige o usuário da sessão.

    Tratamento de erros:
        O limite de observações também fica protegido por CHECK no banco.
    """
    op.add_column(
        "biblioteca_usuario",
        sa.Column("favorito", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "biblioteca_usuario",
        sa.Column("observacoes_pessoais", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_biblioteca_observacoes_limite",
        "biblioteca_usuario",
        "observacoes_pessoais IS NULL OR char_length(observacoes_pessoais) <= 2000",
    )
    op.create_index(
        "ix_biblioteca_usuario_usuario_favorito",
        "biblioteca_usuario",
        ["usuario_id", "favorito"],
    )


def downgrade() -> None:
    """Remove somente os campos e índice introduzidos por esta revisão."""
    op.drop_index("ix_biblioteca_usuario_usuario_favorito", table_name="biblioteca_usuario")
    op.drop_constraint(
        "ck_biblioteca_observacoes_limite", "biblioteca_usuario", type_="check"
    )
    op.drop_column("biblioteca_usuario", "observacoes_pessoais")
    op.drop_column("biblioteca_usuario", "favorito")
