"""Modelo local de arquivo para novas revisões Alembic."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Aplica a alteração versionada ao esquema PostgreSQL."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reverte somente a revisão definida após avaliação de segurança."""
    ${downgrades if downgrades else "pass"}
