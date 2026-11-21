"""Testes de integração PostgreSQL isolados do banco principal."""

from __future__ import annotations

import os
import unittest
from datetime import date, datetime, timezone
from uuid import uuid4
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from backend.database import create_database_engine, get_database_url
from backend.models import BibliotecaUsuario, Livro, ProgressoLeitura, Usuario
from backend.repositories import biblioteca, livros, metas, preferencias, progresso, usuarios

TEST_DATABASE = "biblioteca_inteligente_test"


class RepositoriosPostgreSQLTests(unittest.TestCase):
    """Valida restrições e isolamento em instância PostgreSQL real."""

    @classmethod
    def setUpClass(cls) -> None:
        """Aplica migrações somente na base explicitamente isolada de testes."""
        cls.engine = create_database_engine(TEST_DATABASE)
        if get_database_url(TEST_DATABASE).database != TEST_DATABASE:
            raise RuntimeError("A suíte de integração recusou um destino diferente da base de testes.")
        previous = os.environ.get("BIBLIOTECA_DATABASE_NAME")
        os.environ["BIBLIOTECA_DATABASE_NAME"] = TEST_DATABASE
        try:
            command.upgrade(Config("alembic.ini"), "head")
        finally:
            if previous is None:
                os.environ.pop("BIBLIOTECA_DATABASE_NAME", None)
            else:
                os.environ["BIBLIOTECA_DATABASE_NAME"] = previous

    @classmethod
    def tearDownClass(cls) -> None:
        """Libera o pool sem remover o banco de testes nem sua revisão."""
        cls.engine.dispose()

    def setUp(self) -> None:
        """Abre transação que será revertida após cada caso de teste."""
        self.session = Session(self.engine)
        self.transaction = self.session.begin()

    def test_vercel_requires_explicit_secure_neon_urls(self) -> None:
        """Confirma URLs remotas explícitas e TLS sem fallback para localhost."""
        with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
            os.environ.pop("DATABASE_URL", None)
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                get_database_url()
        with patch.dict(os.environ, {
            "VERCEL": "1",
            "DATABASE_URL": "postgresql://app:secret@ep-example-pooler.neon.tech/library?sslmode=disable",
            "DATABASE_URL_ADMIN": "postgresql://admin:secret@ep-example.neon.tech/library",
        }, clear=False):
            app_url = get_database_url()
            admin_url = get_database_url(administrative=True)
            self.assertEqual(app_url.host, "ep-example-pooler.neon.tech")
            self.assertEqual(app_url.query["sslmode"], "require")
            self.assertEqual(admin_url.username, "admin")
            os.environ["DATABASE_URL"] = "postgresql://app:secret@127.0.0.1/library"
            with self.assertRaisesRegex(RuntimeError, "local"):
                get_database_url()

    def tearDown(self) -> None:
        """Reverte dados temporários para manter a base de testes limpa."""
        if self.transaction.is_active:
            self.transaction.rollback()
        self.session.close()

    def criar_usuario(self, username: str | None = None) -> Usuario:
        """Cria conta isolada com hash Werkzeug para os cenários da suíte."""
        return usuarios.criar_usuario(
            self.session,
            nome="Pessoa de Teste",
            nome_usuario=username or f"teste_{uuid4().hex[:12]}",
            senha_hash=generate_password_hash("senha-descartavel-de-teste"),
        )

    def criar_livro(self, **overrides: object) -> Livro:
        """Cria edição temporária e permite substituir seus metadados de teste."""
        values: dict[str, object] = {
            "titulo": f"Livro de teste {uuid4().hex[:8]}",
            "autores": ["Autora de Teste"],
            "assuntos": ["ficção"],
        }
        values.update(overrides)
        return livros.criar_livro(self.session, **values)  # type: ignore[arg-type]

    def test_migration_tables_and_authenticated_connection(self) -> None:
        """Confirma conexão real, versão aplicada e seis tabelas de domínio."""
        current = self.session.execute(text("SELECT current_database(), current_user")).one()
        self.assertEqual(current[0], TEST_DATABASE)
        self.assertNotEqual(current[1], "postgres")
        tables = set(inspect(self.engine).get_table_names(schema="public"))
        self.assertTrue(
            {
                "usuarios",
                "livros",
                "biblioteca_usuario",
                "progresso_leitura",
                "metas_leitura",
                "preferencias",
                "alembic_version",
            }.issubset(tables)
        )
        revision = self.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        self.assertTrue(revision)
        self.assertFalse(
            self.session.execute(
                text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            ).scalar_one()
        )
        owners = self.session.execute(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname IN ('usuarios','livros') "
                "AND pg_get_userbyid(c.relowner)='biblioteca_app'"
            )
        ).scalar_one()
        self.assertEqual(owners, 0)

    def test_user_hash_normalization_uniqueness_and_update(self) -> None:
        """Confirma hash, canonicalização, unicidade e atualização do perfil."""
        account = self.criar_usuario("  LeitorÁvido  ")
        self.assertEqual(account.nome_usuario, "leitorávido")
        self.assertTrue(account.senha_hash.startswith("scrypt:") or account.senha_hash.startswith("pbkdf2:"))
        self.assertIsNotNone(usuarios.obter_usuario_por_nome(self.session, "LEITORÁVIDO"))
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                usuarios.criar_usuario(
                    self.session,
                    nome="Duplicado",
                    nome_usuario="LEITORÁVIDO",
                    senha_hash=generate_password_hash("senha-descartavel-de-teste"),
                )
        changed = usuarios.atualizar_perfil(self.session, usuario_id=account.id, nome="Nome atualizado")
        self.assertEqual(changed.nome, "Nome atualizado")
        with self.assertRaises(ValueError):
            usuarios.criar_usuario(self.session, nome="X", nome_usuario="sem_hash", senha_hash="senha-pura")

    def test_books_without_isbn_and_editions_are_not_deduplicated_by_title(self) -> None:
        """Permite ISBN ausente e títulos iguais para edições independentes."""
        first = self.criar_livro(titulo="Mesmo título", isbn=None, identificador_externo="OL1M", origem_catalogo="openlibrary")
        second = self.criar_livro(titulo="Mesmo título", isbn=None, identificador_externo="OL2M", origem_catalogo="openlibrary")
        self.assertNotEqual(first.id, second.id)
        self.assertIsNone(first.isbn)
        self.assertCountEqual(livros.pesquisar_livros(self.session, titulo="Mesmo título"), [first, second])
        changed = livros.atualizar_livro(self.session, livro_id=first.id, titulo="Título revisado", descricao="Descrição")
        self.assertEqual(changed.titulo, "Título revisado")
        owner = self.criar_usuario()
        biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=first.id)
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                livros.remover_livro_sem_associacoes(self.session, livro_id=first.id)

    def test_catalog_identifier_and_normalized_isbn_prevent_duplicate_editions(self) -> None:
        """Aplica unicidade por identificador externo e ISBN normalizado."""
        self.criar_livro(titulo="Primeira edição", isbn="978-0-306-40615-7", identificador_externo="OLX", origem_catalogo="openlibrary")
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                self.criar_livro(titulo="ISBN repetido", isbn="9780306406157")
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                self.criar_livro(titulo="Identificador repetido", isbn=None, identificador_externo="OLX", origem_catalogo="openlibrary")
        with self.assertRaises(ValueError):
            self.criar_livro(titulo="ISBN inválido", isbn="123")

    def test_database_rejects_noncanonical_isbn_and_nonarray_catalog_fields(self) -> None:
        """Confirma restrições PostgreSQL independentes da validação Python."""
        with self.session.begin_nested():
            self.session.add(
                Livro(
                    titulo="ISBN fora do formato canônico",
                    isbn="978-0306406157",
                    autores=[],
                    generos=[],
                    assuntos=[],
                )
            )
            with self.assertRaises(IntegrityError):
                self.session.flush()
        with self.session.begin_nested():
            self.session.add(
                Livro(
                    titulo="Autores fora do formato de lista",
                    autores={"autor": "Inesperado"},  # type: ignore[arg-type]
                    generos=[],
                    assuntos=[],
                )
            )
            with self.assertRaises(IntegrityError):
                self.session.flush()

    def test_foreign_keys_reject_missing_owner_or_book(self) -> None:
        """Confirma que o PostgreSQL impede associação com chaves órfãs."""
        with self.session.begin_nested():
            self.session.add(BibliotecaUsuario(usuario_id=uuid4(), livro_id=uuid4()))
            with self.assertRaises(IntegrityError):
                self.session.flush()

    def test_library_isolation_duplicate_add_and_owner_scoped_removal(self) -> None:
        """Isola listagem, consulta e exclusão da biblioteca por proprietário."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        book = self.criar_livro()
        item = biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=book.id)
        duplicate = biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=book.id)
        other_item = biblioteca.adicionar_livro(self.session, usuario_id=other.id, livro_id=book.id)
        self.assertEqual(item.id, duplicate.id)
        self.assertEqual(len(biblioteca.listar_livros_usuario(self.session, usuario_id=owner.id)), 1)
        self.assertEqual(len(biblioteca.listar_livros_usuario(self.session, usuario_id=other.id)), 1)
        self.assertIsNone(biblioteca.obter_item_usuario(self.session, usuario_id=other.id, item_id=item.id))
        self.assertFalse(biblioteca.remover_livro_usuario(self.session, usuario_id=other.id, item_id=item.id))
        self.assertTrue(biblioteca.remover_livro_usuario(self.session, usuario_id=owner.id, item_id=item.id))
        self.assertIsNotNone(biblioteca.obter_item_usuario(self.session, usuario_id=other.id, item_id=other_item.id))
        self.assertIsNotNone(livros.obter_livro(self.session, book.id))

    def test_library_personal_search_filters_sort_and_pagination(self) -> None:
        """Valida filtros combinados e páginas sempre restritas ao proprietário."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        records = [
            self.criar_livro(titulo="Café e histórias", autores=["Ágata Ramos"], assuntos=["Fantasia"]),
            self.criar_livro(titulo="Aventura no mar", autores=["Bruno Reis"], assuntos=["Aventura"]),
            self.criar_livro(titulo="Café à noite", autores=["Ágata Ramos"], assuntos=["Romance"]),
        ]
        items = [biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=book.id)
                 for book in records]
        items[0].adicionado_em = datetime(2022, 1, 1, tzinfo=timezone.utc)
        items[1].adicionado_em = datetime(2024, 1, 1, tzinfo=timezone.utc)
        items[2].adicionado_em = datetime(2025, 1, 1, tzinfo=timezone.utc)
        items[0].favorito = True
        items[0].observacoes_pessoais = "Leitura privada"
        self.session.flush()
        other_book = self.criar_livro(titulo="Café alheio", autores=["Ágata Ramos"], assuntos=["Fantasia"])
        biblioteca.adicionar_livro(self.session, usuario_id=other.id, livro_id=other_book.id)

        result = biblioteca.listar_pagina_usuario(
            self.session, usuario_id=owner.id, consulta="cafe", autor="agata",
            assunto="fantasia", favoritos=True, ordenacao="titulo_asc", pagina=1, tamanho=1,
        )
        self.assertEqual(result["filtered_total"], 1)
        self.assertEqual(result["total_books"], 3)
        self.assertEqual(result["total_favorites"], 1)
        self.assertEqual(result["entries"][0].id, items[0].id)
        self.assertEqual(items[0].observacoes_pessoais, "Leitura privada")

        first_page = biblioteca.listar_pagina_usuario(
            self.session, usuario_id=owner.id, ordenacao="titulo_asc", pagina=1, tamanho=2,
        )
        second_page = biblioteca.listar_pagina_usuario(
            self.session, usuario_id=owner.id, ordenacao="titulo_asc", pagina=2, tamanho=2,
        )
        self.assertEqual([item.livro.titulo for item in first_page["entries"]],
                         ["Aventura no mar", "Café à noite"])
        self.assertEqual([item.livro.titulo for item in second_page["entries"]], ["Café e histórias"])
        recent = biblioteca.listar_pagina_usuario(
            self.session, usuario_id=owner.id, ordenacao="adicionados_recentes", pagina=1, tamanho=3,
        )
        oldest = biblioteca.listar_pagina_usuario(
            self.session, usuario_id=owner.id, ordenacao="adicionados_antigos", pagina=1, tamanho=3,
        )
        self.assertEqual(recent["entries"][0].id, items[2].id)
        self.assertEqual(oldest["entries"][0].id, items[0].id)

    def test_library_personal_fields_are_owner_scoped_and_database_limited(self) -> None:
        """Persiste favoritos pessoais e aplica limite CHECK às observações."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        book = self.criar_livro()
        item = biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=book.id)
        other_item = biblioteca.adicionar_livro(self.session, usuario_id=other.id, livro_id=book.id)
        self.assertFalse(item.favorito)
        self.assertFalse(other_item.favorito)
        self.assertIsNone(item.observacoes_pessoais)
        self.assertIsNone(biblioteca.atualizar_dados_pessoais(
            self.session, usuario_id=other.id, item_id=item.id, favorito=True
        ))
        updated = biblioteca.atualizar_dados_pessoais(
            self.session, usuario_id=owner.id, item_id=item.id,
            favorito=True, observacoes_pessoais="<script>alert(1)</script>",
            atualizar_observacoes=True,
        )
        self.assertTrue(updated.favorito)
        self.assertFalse(other_item.favorito)
        self.assertEqual(updated.observacoes_pessoais, "<script>alert(1)</script>")
        with self.session.begin_nested():
            updated.observacoes_pessoais = "x" * 2001
            with self.assertRaises(IntegrityError):
                self.session.flush()

    def test_library_management_migration_columns_and_constraints(self) -> None:
        """Confirma colunas pessoais, default e proteção CHECK após a migração."""
        columns = {column["name"]: column for column in inspect(self.engine).get_columns("biblioteca_usuario")}
        self.assertIn("favorito", columns)
        self.assertIn("observacoes_pessoais", columns)
        self.assertFalse(columns["favorito"]["nullable"])
        self.assertIn("false", str(columns["favorito"]["default"]).lower())
        checks = {check["name"] for check in inspect(self.engine).get_check_constraints("biblioteca_usuario")}
        self.assertIn("ck_biblioteca_observacoes_limite", checks)

    def test_progress_validation_constraints_and_owner_scope(self) -> None:
        """Valida estado, total de páginas e leitura sem acesso cruzado."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        book = self.criar_livro()
        item = biblioteca.adicionar_livro(self.session, usuario_id=owner.id, livro_id=book.id)
        record = progresso.salvar_progresso(
            self.session,
            usuario_id=owner.id,
            item_id=item.id,
            status="lendo",
            paginas_lidas=25,
            total_paginas=100,
        )
        self.assertEqual(record.status, "lendo")
        self.assertIsNone(progresso.obter_progresso(self.session, usuario_id=other.id, item_id=item.id))
        with self.assertRaises(ValueError):
            progresso.salvar_progresso(self.session, usuario_id=owner.id, item_id=item.id, status="lendo", paginas_lidas=-1)
        with self.assertRaises(ValueError):
            progresso.salvar_progresso(self.session, usuario_id=owner.id, item_id=item.id, status="lendo", paginas_lidas=101, total_paginas=100)
        with self.session.begin_nested():
            self.session.add(ProgressoLeitura(biblioteca_usuario_id=item.id, status="lendo", paginas_lidas=-1))
            with self.assertRaises(IntegrityError):
                self.session.flush()
        self.assertTrue(biblioteca.remover_livro_usuario(self.session, usuario_id=owner.id, item_id=item.id))
        self.assertIsNone(self.session.get(ProgressoLeitura, record.id))

    def test_goals_validate_periods_and_are_owner_scoped(self) -> None:
        """Testa criação, unicidade, consultas e remoção de metas pessoais."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        start, end = date(2026, 1, 1), date(2026, 12, 31)
        goal = metas.criar_meta(self.session, usuario_id=owner.id, quantidade_objetivo=12, periodo_inicio=start, periodo_fim=end)
        self.assertEqual(metas.listar_metas(self.session, usuario_id=other.id), [])
        with self.assertRaises(ValueError):
            metas.criar_meta(self.session, usuario_id=owner.id, quantidade_objetivo=0, periodo_inicio=start, periodo_fim=end)
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                metas.criar_meta(self.session, usuario_id=owner.id, quantidade_objetivo=5, periodo_inicio=start, periodo_fim=end)
        self.assertFalse(metas.remover_meta(self.session, usuario_id=other.id, meta_id=goal.id))
        self.assertIsNone(
            metas.atualizar_meta(
                self.session,
                usuario_id=other.id,
                meta_id=goal.id,
                quantidade_objetivo=15,
                periodo_inicio=start,
                periodo_fim=end,
            )
        )
        updated = metas.atualizar_meta(
            self.session,
            usuario_id=owner.id,
            meta_id=goal.id,
            quantidade_objetivo=15,
            periodo_inicio=start,
            periodo_fim=end,
        )
        self.assertEqual(updated.quantidade_objetivo, 15)
        self.assertTrue(metas.remover_meta(self.session, usuario_id=owner.id, meta_id=goal.id))

    def test_preferences_are_unique_validated_and_owner_scoped(self) -> None:
        """Testa catálogo curto de preferências, nível e separação por dono."""
        owner, other = self.criar_usuario(), self.criar_usuario()
        preference = preferencias.criar_preferencia(
            self.session, usuario_id=owner.id, categoria="Assunto", valor="Fantasia", nivel=5
        )
        self.assertEqual(preference.usuario_id, owner.id)
        self.assertEqual(preferencias.listar_preferencias(self.session, usuario_id=other.id), [])
        with self.assertRaises(ValueError):
            preferencias.criar_preferencia(self.session, usuario_id=owner.id, categoria="outro", valor="Tema")
        with self.session.begin_nested():
            with self.assertRaises(IntegrityError):
                preferencias.criar_preferencia(self.session, usuario_id=owner.id, categoria="assunto", valor="FANTASIA")
        changed = preferencias.atualizar_nivel_preferencia(
            self.session, usuario_id=owner.id, preferencia_id=preference.id, nivel=2
        )
        self.assertEqual(changed.nivel, 2)
        self.assertFalse(preferencias.remover_preferencia(self.session, usuario_id=other.id, preferencia_id=preference.id))
        self.assertTrue(preferencias.remover_preferencia(self.session, usuario_id=owner.id, preferencia_id=preference.id))

    def test_connection_failure_is_reported_without_fallback(self) -> None:
        """Confirma que conexão indisponível falha sem cair em armazenamento alternativo."""
        url = get_database_url(TEST_DATABASE).set(port=1)
        failing_engine = create_engine(url, connect_args={"connect_timeout": 1})
        try:
            with self.assertRaises(OperationalError):
                failing_engine.connect()
        finally:
            failing_engine.dispose()
if __name__ == "__main__":
    unittest.main()
