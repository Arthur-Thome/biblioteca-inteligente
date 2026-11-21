"""Registra a classificação de origem da obra por associação de biblioteca."""

from alembic import op
import sqlalchemy as sa

revision = "d1a45f8c2e70"
down_revision = "c4e8a19f07d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adiciona origem individual com padrão seguro para itens existentes.

    Retorno:
        Nenhum valor; cada associação recebe `nao_informado` sem perder campos.

    Integração:
        O modelo e o repositório filtram e alteram a classificação vinculada
        ao usuário, sem modificar o livro bibliográfico compartilhado.

    Tratamento de erros:
        CHECK do PostgreSQL rejeita códigos fora dos três valores permitidos.
    """
    op.add_column(
        "biblioteca_usuario",
        sa.Column(
            "origem_obra",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'nao_informado'"),
        ),
    )
    op.create_check_constraint(
        "ck_biblioteca_origem_obra",
        "biblioteca_usuario",
        "origem_obra IN ('nacional', 'internacional', 'nao_informado')",
    )
    op.create_index(
        "ix_biblioteca_usuario_usuario_origem",
        "biblioteca_usuario",
        ["usuario_id", "origem_obra"],
    )


def downgrade() -> None:
    """Remove a classificação da revisão após reversão administrada."""
    op.drop_index("ix_biblioteca_usuario_usuario_origem", table_name="biblioteca_usuario")
    op.drop_constraint("ck_biblioteca_origem_obra", "biblioteca_usuario", type_="check")
    op.drop_column("biblioteca_usuario", "origem_obra")
