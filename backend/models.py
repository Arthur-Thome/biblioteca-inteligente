"""Modelos relacionais iniciais do domínio Biblioteca Inteligente."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa comum para metadados e migrações Alembic."""


json_documents = JSON().with_variant(JSONB(), "postgresql")


class TimestampMixin:
    """Campos de auditoria temporal armazenados como timestamp com fuso."""

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Usuario(TimestampMixin, Base):
    """Conta individual com nome normalizado e hash de senha Werkzeug."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("nome_usuario = lower(btrim(nome_usuario))", name="ck_usuarios_nome_canonico"),
        CheckConstraint("length(btrim(nome)) > 0", name="ck_usuarios_nome_nao_vazio"),
        CheckConstraint("length(senha_hash) > 0", name="ck_usuarios_hash_nao_vazio"),
        Index("uq_usuarios_nome_usuario", "nome_usuario", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    nome_usuario: Mapped[str] = mapped_column(String(80), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    biblioteca: Mapped[list["BibliotecaUsuario"]] = relationship(back_populates="usuario")
    metas: Mapped[list["MetaLeitura"]] = relationship(back_populates="usuario")
    preferencias: Mapped[list["Preferencia"]] = relationship(back_populates="usuario")


class Livro(TimestampMixin, Base):
    """Registro bibliográfico de obra ou edição com escopo preservado nos metadados."""

    __tablename__ = "livros"
    __table_args__ = (
        CheckConstraint("length(btrim(titulo)) > 0", name="ck_livros_titulo_nao_vazio"),
        CheckConstraint("ano_publicacao IS NULL OR ano_publicacao BETWEEN 0 AND 9999", name="ck_livros_ano_valido"),
        CheckConstraint(
            "isbn IS NULL OR (isbn = upper(btrim(isbn)) "
            "AND isbn ~ '^(?:[0-9]{9}[0-9X]|[0-9]{13})$')",
            name="ck_livros_isbn_canonico",
        ),
        CheckConstraint("jsonb_typeof(autores) = 'array'", name="ck_livros_autores_array"),
        CheckConstraint("jsonb_typeof(generos) = 'array'", name="ck_livros_generos_array"),
        CheckConstraint("jsonb_typeof(assuntos) = 'array'", name="ck_livros_assuntos_array"),
        Index(
            "uq_livros_catalogo_externo",
            "origem_catalogo",
            "identificador_externo",
            unique=True,
            postgresql_where=text("origem_catalogo IS NOT NULL AND identificador_externo IS NOT NULL"),
        ),
        Index(
            "uq_livros_isbn_normalizado",
            text("upper(regexp_replace(isbn, '[^0-9X]', '', 'g'))"),
            unique=True,
            postgresql_where=text("isbn IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    autores: Mapped[list[str]] = mapped_column(json_documents, nullable=False, default=list)
    descricao: Mapped[str | None] = mapped_column(Text)
    isbn: Mapped[str | None] = mapped_column(String(32))
    identificador_externo: Mapped[str | None] = mapped_column(String(250))
    origem_catalogo: Mapped[str | None] = mapped_column(String(80))
    url_capa: Mapped[str | None] = mapped_column(Text)
    ano_publicacao: Mapped[int | None] = mapped_column(Integer)
    generos: Mapped[list[str]] = mapped_column(json_documents, nullable=False, default=list)
    assuntos: Mapped[list[str]] = mapped_column(json_documents, nullable=False, default=list)
    metadados: Mapped[dict[str, Any]] = mapped_column(json_documents, nullable=False, default=dict)

    itens_biblioteca: Mapped[list["BibliotecaUsuario"]] = relationship(back_populates="livro")


class BibliotecaUsuario(TimestampMixin, Base):
    """Associação exclusiva entre uma conta e um registro bibliográfico."""

    __tablename__ = "biblioteca_usuario"
    __table_args__ = (
        UniqueConstraint("usuario_id", "livro_id", name="uq_biblioteca_usuario_livro"),
        Index("ix_biblioteca_usuario_usuario_adicionado", "usuario_id", "adicionado_em"),
        Index("ix_biblioteca_usuario_usuario_favorito", "usuario_id", "favorito"),
        CheckConstraint(
            "observacoes_pessoais IS NULL OR char_length(observacoes_pessoais) <= 2000",
            name="ck_biblioteca_observacoes_limite",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    livro_id: Mapped[UUID] = mapped_column(ForeignKey("livros.id", ondelete="RESTRICT"), nullable=False)
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    favorito: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    observacoes_pessoais: Mapped[str | None] = mapped_column(Text)

    usuario: Mapped[Usuario] = relationship(back_populates="biblioteca")
    livro: Mapped[Livro] = relationship(back_populates="itens_biblioteca")
    progresso: Mapped["ProgressoLeitura | None"] = relationship(back_populates="item_biblioteca", uselist=False)


class ProgressoLeitura(TimestampMixin, Base):
    """Estado de leitura cuja coluna status é a única fonte de verdade."""

    __tablename__ = "progresso_leitura"
    __table_args__ = (
        UniqueConstraint("biblioteca_usuario_id", name="uq_progresso_item_biblioteca"),
        CheckConstraint("status IN ('nao_iniciado', 'lendo', 'concluido', 'abandonado')", name="ck_progresso_status"),
        CheckConstraint("paginas_lidas >= 0", name="ck_progresso_paginas_nao_negativas"),
        CheckConstraint("total_paginas IS NULL OR total_paginas > 0", name="ck_progresso_total_positivo"),
        CheckConstraint("total_paginas IS NULL OR paginas_lidas <= total_paginas", name="ck_progresso_limite_paginas"),
        CheckConstraint("concluido_em IS NULL OR iniciado_em IS NULL OR concluido_em >= iniciado_em", name="ck_progresso_datas"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    biblioteca_usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("biblioteca_usuario.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="nao_iniciado")
    paginas_lidas: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_paginas: Mapped[int | None] = mapped_column(Integer)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observacoes: Mapped[str | None] = mapped_column(Text)

    item_biblioteca: Mapped[BibliotecaUsuario] = relationship(back_populates="progresso")


class MetaLeitura(TimestampMixin, Base):
    """Meta pessoal por período, com progresso derivado dos registros de leitura."""

    __tablename__ = "metas_leitura"
    __table_args__ = (
        CheckConstraint("quantidade_objetivo > 0", name="ck_metas_quantidade_positiva"),
        CheckConstraint("periodo_fim > periodo_inicio", name="ck_metas_periodo_valido"),
        UniqueConstraint("usuario_id", "periodo_inicio", "periodo_fim", name="uq_metas_usuario_periodo"),
        Index("ix_metas_usuario_periodo", "usuario_id", "periodo_inicio", "periodo_fim"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    quantidade_objetivo: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="metas")


class Preferencia(TimestampMixin, Base):
    """Preferência simples de gênero ou assunto pertencente a uma conta."""

    __tablename__ = "preferencias"
    __table_args__ = (
        CheckConstraint("categoria IN ('genero', 'assunto')", name="ck_preferencias_categoria"),
        CheckConstraint("length(btrim(valor)) > 0", name="ck_preferencias_valor_nao_vazio"),
        CheckConstraint("nivel BETWEEN 1 AND 5", name="ck_preferencias_nivel"),
        UniqueConstraint("usuario_id", "categoria", "valor_normalizado", name="uq_preferencias_usuario_valor"),
        Index("ix_preferencias_usuario", "usuario_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    categoria: Mapped[str] = mapped_column(String(12), nullable=False)
    valor: Mapped[str] = mapped_column(String(160), nullable=False)
    valor_normalizado: Mapped[str] = mapped_column(String(160), nullable=False)
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")

    usuario: Mapped[Usuario] = relationship(back_populates="preferencias")
