"""Cria a primeira estrutura relacional, sem transferir registros de navegador."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b86bc6695616'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica a alteração versionada ao esquema PostgreSQL."""
    # Registros bibliográficos são compartilhados; dados pessoais ficam nas
    # associações e tabelas cujo acesso sempre recebe o identificador do dono.
    op.create_table('livros',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('titulo', sa.String(length=500), nullable=False),
    sa.Column('autores', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=True),
    sa.Column('isbn', sa.String(length=32), nullable=True),
    sa.Column('identificador_externo', sa.String(length=250), nullable=True),
    sa.Column('origem_catalogo', sa.String(length=80), nullable=True),
    sa.Column('url_capa', sa.Text(), nullable=True),
    sa.Column('ano_publicacao', sa.Integer(), nullable=True),
    sa.Column('generos', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('assuntos', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('ano_publicacao IS NULL OR ano_publicacao BETWEEN 0 AND 9999', name='ck_livros_ano_valido'),
    sa.CheckConstraint('length(btrim(titulo)) > 0', name='ck_livros_titulo_nao_vazio'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_livros_catalogo_externo', 'livros', ['origem_catalogo', 'identificador_externo'], unique=True, postgresql_where=sa.text('origem_catalogo IS NOT NULL AND identificador_externo IS NOT NULL'))
    op.create_index('uq_livros_isbn_normalizado', 'livros', [sa.literal_column("upper(regexp_replace(isbn, '[^0-9X]', '', 'g'))")], unique=True, postgresql_where=sa.text('isbn IS NOT NULL'))
    op.create_table('usuarios',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('nome', sa.String(length=160), nullable=False),
    sa.Column('nome_usuario', sa.String(length=80), nullable=False),
    sa.Column('senha_hash', sa.String(length=255), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(btrim(nome)) > 0', name='ck_usuarios_nome_nao_vazio'),
    sa.CheckConstraint('length(senha_hash) > 0', name='ck_usuarios_hash_nao_vazio'),
    sa.CheckConstraint('nome_usuario = lower(btrim(nome_usuario))', name='ck_usuarios_nome_canonico'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_usuarios_nome_usuario', 'usuarios', ['nome_usuario'], unique=True)
    op.create_table('biblioteca_usuario',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('livro_id', sa.Uuid(), nullable=False),
    sa.Column('adicionado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['livro_id'], ['livros.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'livro_id', name='uq_biblioteca_usuario_livro')
    )
    op.create_index('ix_biblioteca_usuario_usuario_adicionado', 'biblioteca_usuario', ['usuario_id', 'adicionado_em'], unique=False)
    op.create_table('metas_leitura',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('quantidade_objetivo', sa.Integer(), nullable=False),
    sa.Column('periodo_inicio', sa.Date(), nullable=False),
    sa.Column('periodo_fim', sa.Date(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('periodo_fim > periodo_inicio', name='ck_metas_periodo_valido'),
    sa.CheckConstraint('quantidade_objetivo > 0', name='ck_metas_quantidade_positiva'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'periodo_inicio', 'periodo_fim', name='uq_metas_usuario_periodo')
    )
    op.create_index('ix_metas_usuario_periodo', 'metas_leitura', ['usuario_id', 'periodo_inicio', 'periodo_fim'], unique=False)
    op.create_table('preferencias',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('categoria', sa.String(length=12), nullable=False),
    sa.Column('valor', sa.String(length=160), nullable=False),
    sa.Column('valor_normalizado', sa.String(length=160), nullable=False),
    sa.Column('nivel', sa.Integer(), server_default='3', nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("categoria IN ('genero', 'assunto')", name='ck_preferencias_categoria'),
    sa.CheckConstraint('length(btrim(valor)) > 0', name='ck_preferencias_valor_nao_vazio'),
    sa.CheckConstraint('nivel BETWEEN 1 AND 5', name='ck_preferencias_nivel'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'categoria', 'valor_normalizado', name='uq_preferencias_usuario_valor')
    )
    op.create_index('ix_preferencias_usuario', 'preferencias', ['usuario_id'], unique=False)
    op.create_table('progresso_leitura',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('biblioteca_usuario_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='nao_iniciado', nullable=False),
    sa.Column('paginas_lidas', sa.Integer(), server_default='0', nullable=False),
    sa.Column('total_paginas', sa.Integer(), nullable=True),
    sa.Column('iniciado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('concluido_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('observacoes', sa.Text(), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('nao_iniciado', 'lendo', 'concluido', 'abandonado')", name='ck_progresso_status'),
    sa.CheckConstraint('concluido_em IS NULL OR iniciado_em IS NULL OR concluido_em >= iniciado_em', name='ck_progresso_datas'),
    sa.CheckConstraint('paginas_lidas >= 0', name='ck_progresso_paginas_nao_negativas'),
    sa.CheckConstraint('total_paginas IS NULL OR paginas_lidas <= total_paginas', name='ck_progresso_limite_paginas'),
    sa.CheckConstraint('total_paginas IS NULL OR total_paginas > 0', name='ck_progresso_total_positivo'),
    sa.ForeignKeyConstraint(['biblioteca_usuario_id'], ['biblioteca_usuario.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('biblioteca_usuario_id', name='uq_progresso_item_biblioteca')
    )


def downgrade() -> None:
    """Reverte somente a revisão definida após avaliação de segurança."""
    # A reversão remove a estrutura e, por isso, exige avaliação antes de uso
    # em qualquer banco que já contenha dados.
    op.drop_table('progresso_leitura')
    op.drop_index('ix_preferencias_usuario', table_name='preferencias')
    op.drop_table('preferencias')
    op.drop_index('ix_metas_usuario_periodo', table_name='metas_leitura')
    op.drop_table('metas_leitura')
    op.drop_index('ix_biblioteca_usuario_usuario_adicionado', table_name='biblioteca_usuario')
    op.drop_table('biblioteca_usuario')
    op.drop_index('uq_usuarios_nome_usuario', table_name='usuarios')
    op.drop_table('usuarios')
    op.drop_index('uq_livros_isbn_normalizado', table_name='livros', postgresql_where=sa.text('isbn IS NOT NULL'))
    op.drop_index('uq_livros_catalogo_externo', table_name='livros', postgresql_where=sa.text('origem_catalogo IS NOT NULL AND identificador_externo IS NOT NULL'))
    op.drop_table('livros')
