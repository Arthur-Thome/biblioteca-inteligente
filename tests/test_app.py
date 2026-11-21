"""Testes automatizados sem chamadas obrigatÃ³rias Ã  internet ou modelos OCR."""

import io
import os
import sys
import unittest
from uuid import UUID, uuid4
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as entrypoint
from backend import catalogo, recomendacoes, validacoes, visao_computacional
from backend.database import session_scope
from backend.models import MetaLeitura, Preferencia
from backend.repositories import biblioteca, livros, usuarios


class BibliotecaTests(unittest.TestCase):
    """Verifica contratos HTTP e serviÃ§os desacoplados da aplicaÃ§Ã£o."""

    @classmethod
    def setUpClass(cls):
        """Atualiza apenas a base isolada antes dos testes HTTP dependentes do esquema."""
        from alembic import command
        from alembic.config import Config

        previous = os.environ.get("BIBLIOTECA_DATABASE_NAME")
        os.environ["BIBLIOTECA_DATABASE_NAME"] = "biblioteca_inteligente_test"
        try:
            from backend.database import get_database_url
            if get_database_url().database != "biblioteca_inteligente_test":
                raise RuntimeError("Os testes HTTP recusaram um destino diferente da base de testes.")
            command.upgrade(Config("alembic.ini"), "head")
        finally:
            if previous is None:
                os.environ.pop("BIBLIOTECA_DATABASE_NAME", None)
            else:
                os.environ["BIBLIOTECA_DATABASE_NAME"] = previous

    def test_vercel_factory_uses_secure_cookies_and_a_separate_upload_limit(self):
        """Confirma cookies HTTPS e limite online sem alterar a configuração local."""
        with patch.dict(os.environ, {
            "VERCEL": "1",
            "BIBLIOTECA_SECRET_KEY": "chave-persistente-de-teste-com-mais-de-32-bytes",
        }, clear=False):
            hosted_app = entrypoint.create_app()
        self.assertTrue(hosted_app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(hosted_app.config["MAX_CONTENT_LENGTH"], 3_500_000)
        self.assertFalse(entrypoint.app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(entrypoint.app.config["MAX_CONTENT_LENGTH"], 8 * 1024 * 1024)

    def setUp(self):
        """Prepara uma conta descartÃ¡vel no banco de testes para cada caso."""
        self.previous_database = os.environ.get("BIBLIOTECA_DATABASE_NAME")
        os.environ["BIBLIOTECA_DATABASE_NAME"] = "biblioteca_inteligente_test"
        from backend.database import get_database_url
        self.assertEqual(get_database_url().database, "biblioteca_inteligente_test")
        self.client = entrypoint.app.test_client()
        self.username = f"teste_{uuid4().hex[:16]}"
        self.extra_user_ids = []
        self.created_catalog_ids = []
        self.client.get("/cadastro")
        with self.client.session_transaction() as current:
            csrf = current["csrf_token"]
        response = self.client.post("/cadastro", data={"csrf_token": csrf, "nome": "Conta de Teste",
            "nome_usuario": self.username, "senha": "senha-descartavel-12", "confirmacao": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 302)
        self.client.get("/login")
        with self.client.session_transaction() as current:
            csrf = current["csrf_token"]
        response = self.client.post("/login", data={"csrf_token": csrf, "nome_usuario": self.username,
            "senha": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 302)
        with session_scope() as db:
            self.user_id = usuarios.obter_usuario_por_nome(db, self.username).id

    def tearDown(self):
        """Remove somente a conta e o livro descartÃ¡veis criados neste caso."""
        from sqlalchemy import delete, select
        from backend.models import BibliotecaUsuario, Livro, ProgressoLeitura, Usuario

        with session_scope() as db:
            for owner_id in [self.user_id, *self.extra_user_ids]:
                db.execute(delete(Preferencia).where(Preferencia.usuario_id == owner_id))
                db.execute(delete(MetaLeitura).where(MetaLeitura.usuario_id == owner_id))
                owned_ids = list(
                    db.scalars(
                        select(BibliotecaUsuario.livro_id).where(BibliotecaUsuario.usuario_id == owner_id)
                    )
                )
                db.execute(delete(ProgressoLeitura).where(ProgressoLeitura.biblioteca_usuario_id.in_(
                    select(BibliotecaUsuario.id).where(BibliotecaUsuario.usuario_id == owner_id))))
                db.execute(delete(BibliotecaUsuario).where(BibliotecaUsuario.usuario_id == owner_id))
                if owned_ids:
                    db.execute(delete(Livro).where(Livro.id.in_(owned_ids), ~Livro.itens_biblioteca.any()))
                db.execute(delete(Usuario).where(Usuario.id == owner_id))
            if self.created_catalog_ids:
                db.execute(delete(Livro).where(
                    Livro.origem_catalogo == "openlibrary",
                    Livro.identificador_externo.in_(self.created_catalog_ids),
                    ~Livro.itens_biblioteca.any(),
                ))
        if self.previous_database is None:
            os.environ.pop("BIBLIOTECA_DATABASE_NAME", None)
        else:
            os.environ["BIBLIOTECA_DATABASE_NAME"] = self.previous_database

    def post(self, path, **kwargs):
        """Envia mutaÃ§Ã£o de API com token CSRF ativo da sessÃ£o de teste."""
        with self.client.session_transaction() as current:
            kwargs.setdefault("headers", {})["X-CSRFToken"] = current["csrf_token"]
        return self.client.post(path, **kwargs)

    def add_fixture_book(self):
        """Inclui uma obra fictícia na biblioteca da conta do caso atual."""
        with session_scope() as db:
            book = livros.criar_livro(db, titulo=f"Livro de teste {uuid4().hex[:8]}",
                                      identificador_externo=f"OL{uuid4().int % 100000000}W",
                                      origem_catalogo="openlibrary", assuntos=["Fantasy"])
            biblioteca.adicionar_livro(db, usuario_id=self.user_id, livro_id=book.id)
            return book.id

    def register_client(self, username):
        """Cria e autentica outra conta descartável em um cliente independente."""
        client = entrypoint.app.test_client()
        client.get("/cadastro")
        with client.session_transaction() as current:
            csrf = current["csrf_token"]
        response = client.post("/cadastro", data={"csrf_token": csrf, "nome": "Outra Conta",
            "nome_usuario": username, "senha": "senha-descartavel-12", "confirmacao": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 302)
        client.get("/login")
        with client.session_transaction() as current:
            csrf = current["csrf_token"]
        response = client.post("/login", data={"csrf_token": csrf, "nome_usuario": username,
            "senha": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 302)
        with session_scope() as db:
            self.extra_user_ids.append(usuarios.obter_usuario_por_nome(db, username).id)
        return client

    def test_registration_hash_and_duplicate_username(self):
        """Confirma hash Werkzeug e rejeição de username normalizado repetido."""
        from werkzeug.security import check_password_hash
        with session_scope() as db:
            account = usuarios.obter_usuario_por_nome(db, self.username.upper())
            self.assertTrue(check_password_hash(account.senha_hash, "senha-descartavel-12"))
            self.assertNotEqual(account.senha_hash, "senha-descartavel-12")
        guest = entrypoint.app.test_client()
        guest.get("/cadastro")
        with guest.session_transaction() as current:
            csrf = current["csrf_token"]
        duplicate = guest.post("/cadastro", data={"csrf_token": csrf, "nome": "Duplicada",
            "nome_usuario": self.username.upper(), "senha": "senha-descartavel-12",
            "confirmacao": "senha-descartavel-12"})
        self.assertEqual(duplicate.status_code, 409)

    def test_invalid_registration_and_generic_login_error(self):
        """Confirma validação de senha e mensagem indistinta para credenciais inválidas."""
        guest = entrypoint.app.test_client()
        guest.get("/cadastro")
        with guest.session_transaction() as current:
            csrf = current["csrf_token"]
        invalid = guest.post("/cadastro", data={"csrf_token": csrf, "nome": "Inválida",
            "nome_usuario": "invalida", "senha": "curta", "confirmacao": "outra"})
        self.assertEqual(invalid.status_code, 400)
        login_client = entrypoint.app.test_client()
        login_client.get("/login")
        with login_client.session_transaction() as current:
            csrf = current["csrf_token"]
        wrong = login_client.post("/login", data={"csrf_token": csrf, "nome_usuario": "desconhecida",
            "senha": "senha-descartavel-12"})
        self.assertEqual(wrong.status_code, 401)
        self.assertIn("Nome de usuário ou senha inválidos".encode(), wrong.data)
        login_client.get("/login")
        with login_client.session_transaction() as current:
            csrf = current["csrf_token"]
        wrong_existing = login_client.post("/login", data={"csrf_token": csrf, "nome_usuario": self.username,
            "senha": "senha-incorreta"})
        self.assertEqual(wrong_existing.status_code, 401)
        self.assertIn("Nome de usuário ou senha inválidos".encode(), wrong_existing.data)

    def test_csrf_and_logout(self):
        """Confirma rejeição de token ausente/incorreto e encerramento da sessão."""
        self.assertEqual(self.client.post("/logout").status_code, 400)
        self.assertEqual(self.client.post("/logout", headers={"X-CSRFToken": "incorreto"}).status_code, 400)
        self.assertEqual(self.client.post("/api/library", json={}).status_code, 400)
        self.assertEqual(
            self.client.post("/api/library", json={}, headers={"X-CSRFToken": "inválido"}).status_code,
            400,
        )
        with self.client.session_transaction() as current:
            csrf = current["csrf_token"]
        response = self.client.post("/logout", data={"csrf_token": csrf})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/api/library").status_code, 401)

    def test_session_cookie_attributes_and_private_identity_validation(self):
        """Confirma atributos do cookie e invalidação de UUID adulterado."""
        cookie = self.client.get_cookie("session")
        self.assertTrue(cookie.http_only)
        self.assertEqual(cookie.same_site, "Lax")
        with self.client.session_transaction() as current:
            self.assertEqual(set(current.keys()), {"usuario_id", "csrf_token", "_permanent"})
            current["usuario_id"] = str(uuid4())
        self.assertEqual(self.client.get("/api/library").status_code, 401)

    def test_login_ignores_external_next_target(self):
        """Confirma que a autenticação não encaminha para destinos externos."""
        guest = entrypoint.app.test_client()
        guest.get("/login?next=https://example.invalid")
        with guest.session_transaction() as current:
            csrf = current["csrf_token"]
        response = guest.post("/login", data={"csrf_token": csrf, "nome_usuario": self.username,
            "senha": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")

    def test_library_persistence_isolation_duplicate_and_ownership(self):
        """Confirma cadastro e isolamento de associações entre duas contas."""
        other = self.register_client(f"outra_{uuid4().hex[:12]}")
        catalog_id = f"OL{uuid4().int % 100000000}W"
        self.created_catalog_ids.append(catalog_id)
        added = self.post("/api/library", json={"catalog_id": catalog_id,
            "title": "Livro exclusivo", "author": "Autora", "subjects": ["Ficção"], "usuario_id": str(uuid4())})
        self.assertEqual(added.status_code, 201)
        self.assertEqual(self.client.get("/api/library").json["books"][0]["title"], "Livro exclusivo")
        duplicate = self.post("/api/library", json={"catalog_id": catalog_id,
            "title": "Livro exclusivo", "author": "Autora", "subjects": ["Ficção"]})
        self.assertEqual(duplicate.status_code, 201)
        self.assertEqual(duplicate.json["id"], added.json["id"])
        self.assertEqual(other.get("/api/library").json["books"], [])
        association_id = added.json["id"]
        with other.session_transaction() as current:
            other_csrf = current["csrf_token"]
        self.assertEqual(other.delete(f"/api/library/{association_id}", headers={
            "X-CSRFToken": other_csrf
        }).status_code, 404)
        with self.client.session_transaction() as current:
            csrf = current["csrf_token"]
        self.assertEqual(
            self.client.delete(f"/api/library/{association_id}", headers={"X-CSRFToken": csrf}).status_code,
            200,
        )

    def patch(self, path, **kwargs):
        """Envia atualização pessoal com o token CSRF ativo da sessão de teste."""
        with self.client.session_transaction() as current:
            kwargs.setdefault("headers", {})["X-CSRFToken"] = current["csrf_token"]
        return self.client.patch(path, **kwargs)

    def put(self, path, **kwargs):
        """Envia atualização PUT com o token CSRF da sessão de teste."""
        with self.client.session_transaction() as current:
            kwargs.setdefault("headers", {})["X-CSRFToken"] = current["csrf_token"]
        return self.client.put(path, **kwargs)

    def test_ods_page_is_public_and_contains_professor_questions_and_sources(self):
        """Confirma acesso público, quatro respostas e referências oficiais na página ODS."""
        anonymous = entrypoint.app.test_client()
        response = anonymous.get("/sobre-ods")
        self.assertEqual(response.status_code, 200)
        for phrase in (
            "Sobre o Projeto", "ODS 4", "meta 4.6", "Ponto de partida: as ODS",
            "Qual ODS foi escolhida e qual meta dela se relaciona com o problema?",
            "Qual é o problema, quem é afetado por ele e por que ele importa?",
            "Como a solução proposta ajuda a enfrentar esse problema?",
            "Por que a inteligência artificial faz sentido aqui?",
            "O sistema precisa nascer do problema, e não o contrário.",
            "https://brasil.un.org/pt-br/sdgs/4", "https://sdgs.un.org/goals/goal4",
            "https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html",
        ):
            self.assertIn(phrase.encode(), response.data)
        self.assertIn(b"/sobre-ods", anonymous.get("/login").data)
        self.assertIn(b"/sobre-ods", anonymous.get("/cadastro").data)
        self.assertIn(b"/sobre-ods", self.client.get("/").data)

    def test_ods_page_presents_reading_and_census_evidence_with_distinct_methods(self):
        """Confirma resultados, populações, definições e fontes independentes na página pública."""
        anonymous = entrypoint.app.test_client()
        response = anonymous.get("/sobre-ods")
        self.assertEqual(response.status_code, 200)
        for phrase in (
            "Leitura e educação no Brasil", "47%", "53%", "5.504 pessoas", "208 municípios",
            "5 anos ou mais", "três meses anteriores", "11,4 milhões", "15 anos ou mais",
            "mesmo que tenha lido nos últimos 12 meses",
            "7,0% desse grupo", "Censo Demográfico 2022", "Instituto Pró-Livro",
            "não demonstram que a Biblioteca Inteligente alfabetiza pessoas",
            "Apresentac%CC%A7a%CC%83o_Retratos_da_Leitura_2024_13-11_SITE.pdf",
            "https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html",
        ):
            self.assertIn(phrase.encode(), response.data)

    def test_reading_progress_validation_completion_and_owner_isolation(self):
        """Valida progresso, datas, percentual, CSRF, sessão e isolamento por conta."""
        self.add_fixture_book()
        listing = self.client.get("/api/library").json["books"][0]
        item_id = listing["id"]
        path = f"/api/library/{item_id}/progress"
        self.assertEqual(self.client.get(path).json["progress"]["status"], "nao_iniciado")
        other = self.register_client(f"progresso_{uuid4().hex[:12]}")
        self.assertEqual(other.get(path).status_code, 404)
        self.assertEqual(self.client.put(path, json={"status": "lendo"}).status_code, 400)
        self.assertEqual(self.put(path, json={"status": "lendo", "pages_read": -1}).status_code, 400)
        self.assertEqual(self.put(path, json={"status": "lendo", "pages_read": 101,
                                             "total_pages": 100}).status_code, 400)
        self.assertEqual(self.put(path, json={"status": "lendo", "started_at": "2026-02-31"}).status_code, 400)
        self.assertEqual(self.put(path, json={"status": "lendo", "started_at": "2999-01-01"}).status_code, 400)
        self.assertEqual(self.client.put(path, json={"status": "lendo"}, headers={
            "X-CSRFToken": "inválido"
        }).status_code, 400)
        reading = self.put(path, json={"status": "lendo", "pages_read": 25,
            "total_pages": 100, "started_at": "2026-11-10"})
        self.assertEqual(reading.status_code, 200)
        self.assertEqual(reading.json["progress"]["progress_percent"], 25)
        self.assertEqual(reading.json["progress"]["started_at"], "2026-11-10")
        bad_order = self.put(path, json={"status": "concluido", "total_pages": 100,
            "started_at": "2026-11-12", "completed_at": "2026-11-11"})
        self.assertEqual(bad_order.status_code, 400)
        completed = self.put(path, json={"status": "concluido", "pages_read": 20,
            "total_pages": 100, "started_at": "2026-11-10", "completed_at": "2026-11-15"})
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json["progress"]["pages_read"], 100)
        self.assertEqual(completed.json["progress"]["progress_percent"], 100)
        self.assertEqual(self.client.get("/api/library").json["books"][0]["progress"]["status"], "concluido")
        with other.session_transaction() as current:
            other_token = current["csrf_token"]
        self.assertEqual(other.put(path, json={"status": "abandonado", "pages_read": 0,
            "total_pages": None}, headers={"X-CSRFToken": other_token}).status_code, 404)
        guest = entrypoint.app.test_client()
        self.assertEqual(guest.get(path).status_code, 401)

    def test_goal_crud_progress_dates_and_owner_isolation(self):
        """Valida metas CRUD e contagem exclusiva de livros concluídos no período."""
        self.add_fixture_book()
        item = self.client.get("/api/library").json["books"][0]
        self.put(f"/api/library/{item['id']}/progress", json={
            "status": "concluido", "pages_read": 0, "total_pages": None,
            "started_at": "2026-11-05", "completed_at": "2026-11-12",
        })
        body = {"target": 3, "start_date": "2026-11-01", "end_date": "2026-11-30"}
        created = self.post("/api/goals", json=body)
        self.assertEqual(created.status_code, 201)
        goal = created.json["goal"]
        self.assertEqual(goal["completed"], 1)
        self.assertEqual(goal["remaining"], 2)
        self.assertEqual(goal["progress_percent"], 33)
        self.assertEqual(self.client.get("/api/goals").json["goals"][0]["id"], goal["id"])
        self.assertEqual(self.post("/api/goals", json=body).status_code, 409)
        self.assertEqual(self.post("/api/goals", json={**body, "target": True}).status_code, 400)
        self.assertEqual(self.post("/api/goals", json={**body, "end_date": "2026-02-31"}).status_code, 400)
        updated_body = {"target": 4, "start_date": "2026-11-01", "end_date": "2026-12-02"}
        updated = self.put(f"/api/goals/{goal['id']}", json=updated_body)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["goal"]["target"], 4)
        other = self.register_client(f"meta_{uuid4().hex[:12]}")
        self.assertEqual(other.get("/api/goals").json["goals"], [])
        with other.session_transaction() as current:
            token = current["csrf_token"]
        self.assertEqual(other.put(f"/api/goals/{goal['id']}", json=updated_body,
                                   headers={"X-CSRFToken": token}).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/goals/{goal['id']}", headers={
            "X-CSRFToken": "inválido"
        }).status_code, 400)
        with self.client.session_transaction() as current:
            token = current["csrf_token"]
        self.assertEqual(self.client.delete(f"/api/goals/{goal['id']}", headers={
            "X-CSRFToken": token
        }).status_code, 200)
        self.assertEqual(self.client.get("/api/goals").json["goals"], [])

    def test_preferences_scope_and_recommendations_exclude_owned_books(self):
        """Usa favorito e preferências em recomendações sem repetir livros próprios."""
        self.add_fixture_book()
        with session_scope() as db:
            item = biblioteca.listar_livros_usuario(db, usuario_id=self.user_id)[0]
            item.favorito = True
        own_title = self.client.get("/api/library").json["books"][0]["title"]
        pref = self.post("/api/preferences", json={
            "category": "assunto", "value": "Fantasy", "level": 5,
        })
        self.assertEqual(pref.status_code, 201)
        self.assertEqual(self.client.get("/api/preferences").json["preferences"][0]["value"], "Fantasy")
        duplicate = self.post("/api/preferences", json={
            "category": "assunto", "value": "fantasy", "level": 4,
        })
        self.assertEqual(duplicate.status_code, 409)
        candidates = [
            {"id": "OL900001W", "title": own_title, "author": "Autoria", "subjects": ["Fantasy"]},
            {"id": "OL900002W", "title": "Nova fantasia", "author": "Outra autoria", "subjects": ["Fantasy"]},
            {"id": "OL900003W", "title": "NOVA FANTASIA", "author": "Terceira autoria", "subjects": ["Fantasy"]},
        ]
        with patch.object(recomendacoes, "search_books", return_value=candidates) as search:
            response = self.post("/api/recommend")
        self.assertEqual(response.status_code, 200)
        titles = [book["title"] for book in response.json["books"]]
        self.assertNotIn(own_title, titles)
        self.assertIn("Nova fantasia", titles)
        self.assertEqual(sum(title.casefold() == "nova fantasia" for title in titles), 1)
        self.assertIn("interesse", response.json["books"][0]["reason"])
        self.assertTrue(search.called)
        other = self.register_client(f"pref_{uuid4().hex[:12]}")
        self.assertEqual(other.get("/api/preferences").json["preferences"], [])
        with self.client.session_transaction() as current:
            token = current["csrf_token"]
        self.assertEqual(self.client.delete(f"/api/preferences/{pref.json['preference']['id']}",
            headers={"X-CSRFToken": token}).status_code, 200)

    def test_library_search_filters_sorting_pagination_and_owner_totals(self):
        """Confirma busca combinada, totais completos e paginação isolada por conta."""
        other = self.register_client(f"colecao_{uuid4().hex[:12]}")
        definitions = [
            ("Café e histórias", ["Ágata Ramos"], ["Fantasia"]),
            ("Aventura no mar", ["Bruno Reis"], ["Aventura"]),
            ("Café à noite", ["Ágata Ramos"], ["Romance"]),
        ]
        with session_scope() as db:
            items = []
            for title, authors, subjects in definitions:
                isbn = "9780306406157" if title == "Café e histórias" else None
                book = livros.criar_livro(db, titulo=title, autores=authors, assuntos=subjects, isbn=isbn)
                items.append(biblioteca.adicionar_livro(db, usuario_id=self.user_id, livro_id=book.id))
            items[0].favorito = True
        with other.session_transaction() as current:
            other_id = UUID(current["usuario_id"])
        with session_scope() as db:
            foreign_book = livros.criar_livro(db, titulo="Café de outra conta", autores=["Ágata Ramos"],
                                              assuntos=["Fantasia"])
            biblioteca.adicionar_livro(db, usuario_id=other_id, livro_id=foreign_book.id)

        response = self.client.get("/api/library?q=cafe&author=agata&subject=fantasia&favorites=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["pagination"]["total"], 1)
        self.assertEqual(response.json["summary"], {"total_books": 3, "total_favorites": 1})
        self.assertEqual(response.json["books"][0]["title"], "Café e histórias")
        self.assertTrue(response.json["books"][0]["favorite"])
        self.assertIsNone(response.json["books"][0]["notes"])
        isbn_result = self.client.get("/api/library?q=978-0-306-40615-7")
        self.assertEqual([book["title"] for book in isbn_result.json["books"]], ["Café e histórias"])

        ordered = self.client.get("/api/library?sort=titulo_asc&page_size=2")
        self.assertEqual([book["title"] for book in ordered.json["books"]], ["Aventura no mar", "Café à noite"])
        self.assertEqual(ordered.json["pagination"]["total_pages"], 2)
        self.assertEqual(self.client.get("/api/library?sort=autor_asc").status_code, 200)
        self.assertEqual(self.client.get("/api/library?page=0").status_code, 400)
        self.assertEqual(self.client.get("/api/library?page=99&page_size=1").status_code, 400)
        self.assertEqual(self.client.get("/api/library?page_size=999").status_code, 400)
        self.assertEqual(self.client.get("/api/library?sort=coluna_arbitraria").status_code, 400)
        self.assertEqual(other.get("/api/library").json["summary"]["total_books"], 1)

    def test_origin_classification_filter_and_timestamp_contract(self):
        """Valida origem por conta, filtros combinados e serialização ISO estável."""
        from sqlalchemy import select
        from backend.models import BibliotecaUsuario

        with session_scope() as db:
            national = livros.criar_livro(db, titulo="Leitura Nacional", autores=["Autora Teste"])
            international = livros.criar_livro(db, titulo="Leitura Internacional", autores=["Autor Teste"])
            first = biblioteca.adicionar_livro(db, usuario_id=self.user_id, livro_id=national.id)
            second = biblioteca.adicionar_livro(db, usuario_id=self.user_id, livro_id=international.id)
            first.favorito = True
            first.origem_obra = "nacional"
            second.origem_obra = "internacional"
            first_id, second_id = first.id, second.id

        response = self.client.get("/api/library?origin=nacional&favorites=true&q=nacional")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.json["books"]], ["Leitura Nacional"])
        self.assertEqual(response.json["books"][0]["origin_obra"], "nacional")
        self.assertEqual(self.client.get("/api/library?origin=desconhecida").status_code, 400)

        path = f"/api/library/{first_id}"
        before = self.client.get(path).json["book"]["updated_at"]
        self.assertTrue(before.endswith("Z"))
        self.assertEqual(self.client.get(path).json["book"]["updated_at"], before)
        self.assertEqual(self.patch(path, json={"origin_obra": "internacional"}).status_code, 200)
        self.assertEqual(self.client.get(path).json["book"]["origin_obra"], "internacional")
        self.assertEqual(self.patch(f"/api/library/{second_id}", json={"origin_obra": "outro"}).status_code, 400)

    def test_library_details_favorites_notes_csrf_and_owner_isolation(self):
        """Valida detalhes, mutações CSRF e privacidade do favorito/observação."""
        book_id = self.add_fixture_book()
        with session_scope() as db:
            from sqlalchemy import select
            item = db.scalar(select(biblioteca.BibliotecaUsuario).where(
                biblioteca.BibliotecaUsuario.usuario_id == self.user_id,
                biblioteca.BibliotecaUsuario.livro_id == book_id,
            ))
            item_id = item.id
        other = self.register_client(f"privada_{uuid4().hex[:12]}")
        path = f"/api/library/{item_id}"
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(other.get(path).status_code, 404)
        with other.session_transaction() as current:
            other_csrf = current["csrf_token"]
        self.assertEqual(other.patch(path, json={"favorite": True}, headers={
            "X-CSRFToken": other_csrf
        }).status_code, 404)
        self.assertEqual(self.client.patch(path, json={"favorite": True}, headers={
            "X-CSRFToken": "inválido"
        }).status_code, 400)
        self.assertEqual(self.patch(path, json={"favorite": "sim"}).status_code, 400)
        self.assertEqual(self.patch(path, json={"other": "campo"}).status_code, 400)
        self.assertEqual(self.patch(path, json={"notes": "x" * 2001}).status_code, 400)
        self.assertEqual(self.patch(path, json={"notes": "<script>alert(1)</script>"}).status_code, 200)
        updated = self.patch(path, json={"favorite": True}).json["book"]
        self.assertTrue(updated["favorite"])
        self.assertEqual(updated["notes"], "<script>alert(1)</script>")
        self.assertEqual(self.client.get(path).json["book"]["notes"], "<script>alert(1)</script>")
        self.assertEqual(other.get(path).status_code, 404)

        anonymous = entrypoint.app.test_client()
        anonymous.get("/")
        with anonymous.session_transaction() as current:
            anonymous_csrf = current["csrf_token"]
        self.assertEqual(anonymous.get(path).status_code, 401)
        self.assertEqual(anonymous.patch(path, json={"favorite": False}, headers={
            "X-CSRFToken": anonymous_csrf
        }).status_code, 401)

    def test_repeated_login_attempts_are_temporarily_limited(self):
        """Confirma bloqueio temporário sem tornar a conta permanentemente indisponível."""
        guest = entrypoint.app.test_client()
        guest.get("/login")
        with guest.session_transaction() as current:
            csrf = current["csrf_token"]
        for _ in range(8):
            response = guest.post("/login", data={"csrf_token": csrf, "nome_usuario": "limite_teste",
                "senha": "senha-incorreta"})
            self.assertEqual(response.status_code, 401)
        blocked = guest.post("/login", data={"csrf_token": csrf, "nome_usuario": "limite_teste",
            "senha": "senha-incorreta"})
        self.assertEqual(blocked.status_code, 429)

    def test_database_outage_returns_controlled_login_error(self):
        """Confirma que a falha PostgreSQL não revela detalhes internos ao login."""
        from unittest.mock import patch
        guest = entrypoint.app.test_client()
        guest.get("/login")
        with guest.session_transaction() as current:
            csrf = current["csrf_token"]
        with patch("backend.routes.session_scope", side_effect=RuntimeError("detalhe privado")):
            response = guest.post("/login", data={"csrf_token": csrf, "nome_usuario": "outro_teste",
                "senha": "senha-descartavel-12"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"detalhe privado", response.data)

    def test_ocr_engine_uses_models_from_project_directory(self):
        """Confirma que RapidOCR recebe a pasta local oficial de modelos."""
        previous_engine = visao_computacional._OCR_ENGINE
        visao_computacional._OCR_ENGINE = None
        try:
            with patch("rapidocr.RapidOCR") as engine_factory:
                instance = visao_computacional.get_ocr_engine()
            engine_factory.assert_called_once_with(
                params={
                    "Global.model_root_dir": str(visao_computacional.OCR_MODEL_DIR)
                }
            )
            self.assertIs(instance, engine_factory.return_value)
        finally:
            visao_computacional._OCR_ENGINE = previous_engine

    def test_app_factory_registers_routes(self):
        """Confirma que a fÃ¡brica registra as rotas da interface e das APIs."""
        rules = {rule.rule for rule in entrypoint.app.url_map.iter_rules()}
        self.assertTrue({"/", "/api/health", "/api/search", "/api/recognize", "/api/recommend"}.issubset(rules))

    def test_home(self):
        """Confirma que a pÃ¡gina principal renderiza o formulÃ¡rio de biblioteca."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Adicionar um livro".encode(), response.data)

    def test_frontend_assets_keep_api_and_storage_contracts(self):
        """Confirma que os ativos servidos mantÃªm endpoints e chave local existentes."""
        script = self.client.get("/static/app.js")
        stylesheet = self.client.get("/static/style.css")
        self.assertEqual(script.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(b"estante-livros-v1", script.data)
        self.assertIn(b"/api/recognize", script.data)
        self.assertIn("Pontuação heurística".encode(), script.data)
        self.assertIn(b"/api/search", script.data)
        self.assertIn(b"/api/recommend", script.data)
        script.close()
        stylesheet.close()

    def test_health(self):
        """Confirma o formato bÃ¡sico do estado publicado pela aplicaÃ§Ã£o."""
        response = self.client.get("/api/health")
        self.assertEqual(response.json["status"], "ok")
        self.assertEqual(response.json["catalog"], "Open Library")

    def test_search_requires_query(self):
        """Confirma que consulta curta recebe erro de validaÃ§Ã£o HTTP 400."""
        self.assertEqual(self.client.get("/api/search?q=x").status_code, 400)

    def test_catalog_transforms_search_response(self):
        """Confirma conversÃ£o do formato de API para o contrato de livro do site."""
        payload = {"docs": [{"key": "/works/OL123W", "title": "O Hobbit", "author_name": ["Tolkien"]}]}
        with patch.object(catalogo, "catalog_get", return_value=payload) as request_mock:
            books = catalogo.search_books("O Hobbit", 10)
        self.assertEqual(books[0]["id"], "OL123W")
        self.assertEqual(books[0]["author"], "Tolkien")
        request_mock.assert_called_once()
        catalogo.search_books.cache_clear()

    def test_catalog_normalizes_rich_metadata_and_authors(self):
        """Confirma normalização de campos editoriais e proveniência Open Library."""
        payload = {"docs": [{"key": "/works/OL123W", "title": "Livro", "subtitle": "Subtítulo",
            "author_name": ["Autora Um", "Autor Dois"], "isbn": ["978-0-306-40615-7"],
            "publisher": ["Editora"], "language": ["por"], "number_of_pages_median": 220}]}
        with patch.object(catalogo, "catalog_get", return_value=payload):
            book = catalogo.search_books("Livro", 10)[0]
        self.assertEqual(book["authors"], ["Autora Um", "Autor Dois"])
        self.assertEqual(book["subtitle"], "Subtítulo")
        self.assertEqual(book["isbn_13"], "978-0-306-40615-7")
        self.assertEqual(book["metadata_sources"]["publisher"], "openlibrary")
        catalogo.search_books.cache_clear()

    def test_catalog_supports_author_and_isbn_queries(self):
        """Confirma a seleção dos parâmetros oficiais de busca do catálogo."""
        with patch.object(catalogo, "catalog_get", return_value={"docs": []}) as request_mock:
            self.assertEqual(catalogo.search_books("Machado de Assis", search_type="author"), ())
            self.assertEqual(catalogo.search_books("9780306406157", search_type="isbn"), ())
        calls = [call.args[1] for call in request_mock.call_args_list]
        self.assertEqual(calls[0]["author"], "Machado de Assis")
        self.assertEqual(calls[1]["isbn"], "9780306406157")
        catalogo.search_books.cache_clear()

    def test_catalog_falls_back_to_tolerant_query_for_ocr_typos(self):
        """Recupera candidatos próximos quando a busca estrita não encontra o título."""
        precise = {"docs": [{"key": "/works/OL100W", "title": "A literature unit for The hobit"}]}
        tolerant = {"docs": [{"key": "/works/OL200W", "title": "The Hobbit",
                              "author_name": ["J. R. R. Tolkien"]}]}
        with patch.object(catalogo, "catalog_get", side_effect=[precise, tolerant]) as request_mock:
            books = catalogo.search_books("The Hobit", search_type="title")
        self.assertEqual([book["title"] for book in books], ["The Hobbit", "A literature unit for The hobit"])
        self.assertEqual(request_mock.call_count, 2)
        self.assertEqual(request_mock.call_args_list[1].args[1]["q"], "The Hobit")
        catalogo.search_books.cache_clear()

    def test_catalog_rejects_invalid_search_type(self):
        """Confirma que tipos de busca não reconhecidos não chegam à API."""
        with self.assertRaises(ValueError):
            catalogo.search_books("consulta", search_type="all")
        catalogo.search_books.cache_clear()

    def test_catalog_deduplicates_only_identical_work_ids(self):
        """Remove duplicatas de mesma obra sem unir registros só por título."""
        payload = {"docs": [
            {"key": "/works/OL123W", "title": "Livro", "author_name": ["Autora"]},
            {"key": "OL123W", "title": "Livro", "author_name": ["Autora"]},
            {"key": "/works/OL456W", "title": "Livro", "author_name": ["Autora"]},
        ]}
        with patch.object(catalogo, "catalog_get", return_value=payload):
            books = catalogo.search_books("Livro repetido")
        self.assertEqual([book["id"] for book in books], ["OL123W", "OL456W"])
        catalogo.search_books.cache_clear()

    def test_isbn_checksum_validation_and_retry_after(self):
        """Confirma checksums ISBN e limite do cabeçalho Retry-After."""
        self.assertEqual(catalogo.normalize_isbn("978-0-306-40615-7"), "9780306406157")
        self.assertIsNone(catalogo.normalize_isbn("9780306406158"))
        self.assertEqual(catalogo._retry_after_header("999999"), "86400")
        self.assertIsNone(catalogo._retry_after_header("invalid"))

    def test_open_library_429_exposes_bounded_retry_after(self):
        """Confirma resposta controlada para limite externo de requisições."""
        response = SimpleNamespace(status_code=429, headers={"Retry-After": "30"})
        with patch.object(catalogo.SESSION, "get", return_value=response), \
             patch.object(catalogo.time, "monotonic", side_effect=[10.0, 10.0]), \
             patch.object(catalogo.time, "sleep"):
            with self.assertRaises(catalogo.CatalogError) as captured:
                catalogo.catalog_get("/search.json", {"title": "Livro"})
        self.assertEqual(captured.exception.retry_after, "30")

    def test_google_books_is_disabled_without_local_key(self):
        """Confirma que Google Books não é consultado sem configuração local."""
        from backend.providers import google_books
        with patch.dict(os.environ, {"GOOGLE_BOOKS_API_KEY": ""}), \
             patch.object(google_books.HTTP, "get") as http_get:
            self.assertFalse(google_books.provider_enabled())
            self.assertEqual(google_books.search_metadata("Livro"), [])
        http_get.assert_not_called()

    def test_google_books_complements_only_exact_isbn_match(self):
        """Confirma que metadados complementares exigem ISBN idêntico."""
        from backend.providers import google_books
        payload = {"docs": [{"key": "/works/OL321W", "title": "Livro", "author_name": ["Autora"],
            "isbn": ["9780306406157"]}]}
        complement = [{"title": "Livro", "subtitle": "Edição identificada", "isbn_13": "9780306406157",
            "publisher": "Editora", "source_id": "volume-edition-1"}]
        with patch.object(catalogo, "catalog_get", return_value=payload), \
             patch.object(google_books, "provider_enabled", return_value=True), \
             patch.object(google_books, "search_metadata", return_value=complement):
            book = catalogo.search_books("Livro", 10)[0]
        self.assertEqual(book["subtitle"], "Edição identificada")
        self.assertEqual(book["metadata_sources"]["subtitle"], "google_books")
        self.assertEqual(book["edition_id"], "volume-edition-1")
        catalogo.search_books.cache_clear()

    def test_google_books_rejects_invalid_json_and_handles_timeout(self):
        """Confirma erros controlados para respostas inválidas e timeout Google."""
        import requests
        from backend.providers import google_books
        with patch.object(google_books, "_api_key", return_value="chave-de-teste"), \
             patch.object(google_books.HTTP, "get") as http_get:
            http_get.return_value.raise_for_status.return_value = None
            http_get.return_value.json.return_value = ["unexpected"]
            with self.assertRaises(google_books.GoogleBooksError):
                google_books.search_metadata("Livro")
            http_get.side_effect = requests.Timeout("timeout")
            with self.assertRaises(google_books.GoogleBooksError):
                google_books.search_metadata("Livro")

    def test_manual_search_supports_author_filter_and_rejects_invalid_type(self):
        """Confirma o parâmetro de busca da interface e validação do endpoint."""
        stub = ({"id": "OL123W", "title": "Livro", "author": "Autoria", "subjects": []},)
        with patch("backend.routes.search_books", return_value=stub) as search_mock:
            response = self.client.get("/api/search?q=Machado&type=author")
        self.assertEqual(response.status_code, 200)
        search_mock.assert_called_once_with("Machado", 10, search_type="author")
        invalid = self.client.get("/api/search?q=Machado&type=invalid")
        self.assertEqual(invalid.status_code, 400)

    def test_confirmed_catalog_metadata_is_saved_to_test_database(self):
        """Confirma persistência de proveniência e campos apenas após confirmação."""
        from backend.models import Livro
        catalog_id = f"OL{uuid4().int % 100000000}W"
        self.created_catalog_ids.append(catalog_id)
        metadata = {"subtitle": "Edição de teste", "publisher": "Editora de teste",
                    "page_count": 200, "metadata_sources": {"publisher": "openlibrary"}}
        response = self.post("/api/library", json={"catalog_id": catalog_id,
            "title": "Livro confirmado", "author": "Autora", "metadata": metadata})
        self.assertEqual(response.status_code, 201)
        with session_scope() as db:
            book = livros.obter_por_catalogo(db, origem="openlibrary", identificador=catalog_id)
            self.assertEqual(book.metadados["subtitle"], "Edição de teste")
            self.assertEqual(book.metadados["metadata_sources"]["publisher"], "openlibrary")

    def test_library_rejects_unknown_metadata_and_invalid_provenance(self):
        """Confirma que payloads bibliográficos não aceitos não são gravados."""
        invalid_field = self.post("/api/library", json={"catalog_id": "OL123W", "title": "Livro",
            "metadata": {"internal_path": "C:\\private"}})
        invalid_source = self.post("/api/library", json={"catalog_id": "OL124W", "title": "Livro",
            "metadata": {"metadata_sources": {"publisher": "untrusted"}}})
        self.assertEqual(invalid_field.status_code, 400)
        self.assertEqual(invalid_source.status_code, 400)

    def test_catalog_empty_and_malformed_documents(self):
        """Confirma resposta vazia quando a API nÃ£o entrega uma lista de documentos."""
        with patch.object(catalogo, "catalog_get", return_value={"docs": None}):
            self.assertEqual(catalogo.search_books("consulta sem resultados"), ())
        catalogo.search_books.cache_clear()

    def test_catalog_connection_error_is_normalized(self):
        """Confirma conversÃ£o de falha de rede em erro de domÃ­nio do catÃ¡logo."""
        import requests

        with self.assertLogs("backend.catalogo", level="WARNING"):
            with patch.object(catalogo.SESSION, "get", side_effect=requests.ConnectionError("offline")):
                with self.assertRaises(catalogo.CatalogError):
                    catalogo.catalog_get("/search.json", {"q": "livro"})

    def test_catalog_timeout_is_normalized(self):
        """Confirma que timeout HTTP vira erro controlado do catálogo."""
        import requests

        with self.assertLogs("backend.catalogo", level="WARNING"):
            with patch.object(catalogo.SESSION, "get", side_effect=requests.Timeout("timeout")):
                with self.assertRaises(catalogo.CatalogError):
                    catalogo.catalog_get("/search.json", {"q": "livro"})

    def test_invalid_image_is_rejected(self):
        """Confirma rejeiÃ§Ã£o de bytes que nÃ£o representam imagem vÃ¡lida."""
        self.assertFalse(validacoes.validate_image_bytes("arquivo invÃ¡lido".encode("utf-8")))
        response = self.post("/api/recognize", data={"image": (io.BytesIO(b"not image"), "foto.jpg")})
        self.assertEqual(response.status_code, 400)

    def test_unsupported_image_format_is_rejected(self):
        """Confirma alinhamento do backend com formatos aceitos pela interface."""
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), "white").save(buffer, "BMP")
        self.assertFalse(validacoes.validate_image_bytes(buffer.getvalue()))

    def test_image_pixel_limit_rejects_oversized_dimensions(self):
        """Confirma rejeição do limite de pixels antes de iniciar o mecanismo OCR."""
        buffer = io.BytesIO()
        Image.new("L", (6400, 6400), 255).save(buffer, "PNG", optimize=True)
        self.assertFalse(validacoes.validate_image_bytes(buffer.getvalue()))

    def test_ocr_real_blank_image_returns_no_detections(self):
        """Executa RapidOCR local numa imagem branca e confirma resultado vazio."""
        buffer = io.BytesIO()
        Image.new("RGB", (320, 480), "white").save(buffer, "PNG")
        self.assertEqual(visao_computacional.extract_cover_text(buffer.getvalue()), [])

    def test_ocr_real_low_quality_image_returns_bounded_detections(self):
        """Executa RapidOCR local numa capa reduzida e degradada sem supor acerto."""
        from pathlib import Path
        from PIL import ImageFilter

        fixture = Path(__file__).parent / "fixtures" / "ocr" / "hobbit-capa-evidencia.png"
        with Image.open(fixture) as cover:
            degraded = cover.resize((20, 32)).filter(ImageFilter.GaussianBlur(1.5))
            buffer = io.BytesIO()
            degraded.save(buffer, "JPEG", quality=8)
        detections = visao_computacional.extract_cover_text(buffer.getvalue())
        self.assertIsInstance(detections, list)
        self.assertLessEqual(len(detections), 30)

    def test_ocr_failure_returns_controlled_error(self):
        """Confirma que falha de inicializaÃ§Ã£o OCR nÃ£o expÃµe detalhes internos."""
        buffer = io.BytesIO()
        Image.new("RGB", (40, 40), "white").save(buffer, "PNG")
        buffer.seek(0)
        with self.assertLogs("backend.routes", level="ERROR"):
            with patch("backend.routes.get_ocr_engine", side_effect=RuntimeError("internal detail")):
                response = self.post("/api/recognize", data={"image": (buffer, "capa.png")})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("internal detail", response.json["error"])

    def test_empty_image_and_missing_upload_are_rejected(self):
        """Confirma respostas controladas para upload ausente ou sem conteÃºdo."""
        self.assertEqual(self.post("/api/recognize").status_code, 400)
        response = self.post("/api/recognize", data={"image": (io.BytesIO(b""), "foto.jpg")})
        self.assertEqual(response.status_code, 400)

    def test_upload_limit_returns_json(self):
        """Confirma o limite de oito megabytes e o formato JSON do erro 413."""
        boundary = "limite-de-upload"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"grande.jpg\"\r\n"
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode("ascii") + b"x" * (8 * 1024 * 1024 + 1) + f"\r\n--{boundary}--\r\n".encode("ascii")
        response = self.client.open(
            "/api/recognize",
            method="POST",
            environ_overrides={
                "wsgi.input": io.BytesIO(body),
                "CONTENT_LENGTH": str(len(body)),
                "CONTENT_TYPE": f"multipart/form-data; boundary={boundary}",
            },
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.json)

    def test_ocr_prepares_image_and_filters_confidence(self):
        """Confirma preparaÃ§Ã£o RGB da imagem e filtro das detecÃ§Ãµes por confianÃ§a."""
        buffer = io.BytesIO()
        Image.new("RGB", (200, 270), "white").save(buffer, "PNG")
        engine = lambda bitmap: SimpleNamespace(txts=["O Hobbit", "ruÃ­do"], scores=[0.99, 0.1])
        with patch.object(
            visao_computacional,
            "get_ocr_engine",
            side_effect=lambda: engine if not visao_computacional.OCR_LOCK.locked()
            else self.fail("A inicializaÃ§Ã£o OCR nÃ£o pode ocorrer dentro do lock de inferÃªncia."),
        ):
            entries = visao_computacional.extract_cover_text(buffer.getvalue())
        self.assertEqual(entries, [{"text": "O Hobbit", "confidence": 0.99}])

    def test_ocr_orders_lines_by_position_and_rejects_invalid_confidence(self):
        """Confirma ordenação espacial e descarte de confiança não finita."""
        import numpy as np

        buffer = io.BytesIO()
        Image.new("RGB", (200, 270), "white").save(buffer, "PNG")
        result = SimpleNamespace(
            txts=["linha inferior", "linha superior", "confiança inválida"],
            scores=[0.95, 0.91, float("nan")],
            boxes=np.array([
                [[5, 100], [90, 100], [90, 120], [5, 120]],
                [[80, 10], [180, 10], [180, 30], [80, 30]],
                [[5, 150], [80, 150], [80, 170], [5, 170]],
            ]),
        )
        with patch.object(visao_computacional, "get_ocr_engine", return_value=lambda _bitmap: result):
            entries = visao_computacional.extract_cover_text(buffer.getvalue())
        self.assertEqual([entry["text"] for entry in entries], ["linha superior", "linha inferior"])

    def test_ocr_author_is_only_a_limited_ranking_signal(self):
        """Confirma reforço limitado do autor e ausência de acerto por autor isolado."""
        recognized = "HOBIT JRRTOLKIEN"
        without_author = visao_computacional.score_ocr_match({"title": "The Hobbit"}, recognized)
        with_author = visao_computacional.score_ocr_match(
            {"title": "The Hobbit", "author": "J.R.R. Tolkien"}, recognized
        )
        unrelated_title = visao_computacional.score_ocr_match(
            {"title": "The Silmarillion", "author": "J.R.R. Tolkien"}, "JRRTOLKIEN"
        )
        self.assertGreater(with_author, without_author)
        self.assertLessEqual(with_author - without_author, 12.0)
        self.assertLess(unrelated_title, 50.0)

    def test_ocr_author_evidence_ranks_same_title_by_matching_author(self):
        """Reduz candidatos de mesmo título quando outro autor aparece na capa."""
        recognized = "THE HOBBIT JRR TOLKIEN"
        matching = visao_computacional.score_ocr_match(
            {"title": "The Hobbit", "authors": ["J.R.R. Tolkien"]}, recognized,
            penalize_author_mismatch=True,
        )
        conflicting = visao_computacional.score_ocr_match(
            {"title": "The Hobbit", "authors": ["Jude Fisher"]}, recognized,
            penalize_author_mismatch=True,
        )
        title_only = visao_computacional.score_ocr_match(
            {"title": "The Hobbit", "authors": ["Jude Fisher"]}, "THE HOBBIT",
            penalize_author_mismatch=False,
        )
        self.assertGreater(matching, conflicting)
        self.assertGreater(title_only, conflicting)

    def test_single_common_word_title_requires_exact_token(self):
        """Confirma rejeição de títulos curtos sem token exato no texto OCR."""
        score = visao_computacional.score_ocr_match(
            {"title": "The"}, "The Authorized Edition of The Hobbit"
        )
        self.assertLess(score, 50.0)

    def test_text_queries_are_combined_and_bounded(self):
        """Confirma combinaÃ§Ã£o de linhas e limite de consultas OCR distintas."""
        queries = visao_computacional.suggest_search_queries(["O Senhor", "dos AnÃ©is", " Tolkien"])
        self.assertLessEqual(len(queries), 3)
        self.assertIn("O Senhor dos AnÃ©is", queries)

    def test_text_queries_prioritize_high_confidence_title_fragments(self):
        """Confirma que uma palavra forte da capa não some em combinações ruidosas."""
        queries = visao_computacional.suggest_search_queries([
            {"text": "mTATEEPE", "confidence": 0.531},
            {"text": "HOBBIT", "confidence": 1.0},
            {"text": "THE ENOHIAVTING PERLIDE TO", "confidence": 0.873},
            {"text": "JRRTOLKIEN", "confidence": 0.996},
        ])
        self.assertEqual(queries[0], "HOBBIT")
        self.assertLessEqual(len(queries), 3)

    def test_ocr_match_threshold_keeps_title_and_filters_common_word_noise(self):
        """Confirma que o tÃ­tulo real supera o limiar e um falso positivo comum fica abaixo."""
        recognized = "THE AUTHORIZED EDITION THE HOBBIT THE ENCHANTING PRELUDE JRRTOLKIEN"
        correct = {"title": "The Hobbit"}
        noise = {"title": "The United States in Literature -- The Glass Menagerie Edition"}
        self.assertGreaterEqual(visao_computacional.score_ocr_match(correct, recognized), 50)
        self.assertLess(visao_computacional.score_ocr_match(noise, recognized), 50)

    def test_ocr_endpoint_contract_is_preserved(self):
        """Confirma os campos JSON existentes apÃ³s simular OCR e catÃ¡logo."""
        buffer = io.BytesIO()
        Image.new("RGB", (200, 270), "white").save(buffer, "PNG")
        buffer.seek(0)
        stub = ({"id": "OL123W", "title": "O Hobbit", "author": "Tolkien", "subjects": ["Fantasy"]},)
        with patch("backend.routes.get_ocr_engine"), \
             patch("backend.routes.extract_cover_text", return_value=[{"text": "O Hobbit", "confidence": 0.99}]), \
             patch("backend.routes.search_books", return_value=stub):
            response = self.post("/api/recognize", data={"image": (buffer, "capa.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {"detected", "books", "queries", "message"})
        self.assertEqual(response.json["books"][0]["title"], "O Hobbit")

    def test_recognize_without_text_skips_catalog_and_returns_guidance(self):
        """Confirma mensagem recuperável quando RapidOCR não identifica texto."""
        buffer = io.BytesIO()
        Image.new("RGB", (40, 60), "white").save(buffer, "PNG")
        buffer.seek(0)
        with patch("backend.routes.get_ocr_engine"), \
             patch("backend.routes.extract_cover_text", return_value=[]), \
             patch("backend.routes.search_books") as search:
            response = self.post("/api/recognize", data={"image": (buffer, "capa.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["books"], [])
        self.assertTrue(response.json["message"])
        search.assert_not_called()

    def test_recognize_filters_candidates_below_heuristic_threshold(self):
        """Confirma que candidatos não relacionados não viram identificações seguras."""
        buffer = io.BytesIO()
        Image.new("RGB", (40, 60), "white").save(buffer, "PNG")
        buffer.seek(0)
        unrelated = ({"id": "OL999W", "title": "The Silmarillion", "author": "Unknown", "subjects": []},)
        with patch("backend.routes.get_ocr_engine"), \
             patch("backend.routes.extract_cover_text", return_value=[
                 {"text": "HOBBIT JRRTOLKIEN", "confidence": 0.99}
             ]), \
             patch("backend.routes.search_books", return_value=unrelated):
            response = self.post("/api/recognize", data={"image": (buffer, "capa.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["books"], [])
        self.assertIn("busca manual", response.json["message"])

    def test_recommendation_payload_is_sanitized(self):
        """Confirma que propriedades malformadas nÃ£o provocam exceÃ§Ã£o na validaÃ§Ã£o."""
        books = validacoes.valid_books([
            {"id": "/works/OL123W", "subjects": "texto inesperado", "author": 42},
            {"id": "invÃ¡lido", "subjects": ["Fantasy"]},
            {"id": "OL456W", "subjects": [None, "Fantasy"], "author": "Autor"},
            None,
        ])
        self.assertEqual(books, [
            {"id": "OL123W", "subjects": [], "author": ""},
            {"id": "OL456W", "subjects": ["Fantasy"], "author": "Autor"},
        ])

    def test_recommend_route_rejects_invalid_json_shapes(self):
        """Confirma respostas 400 para JSON malformado ou lista no campo books."""
        self.assertEqual(self.post("/api/recommend", data="{", content_type="application/json").status_code, 400)
        response = self.post("/api/recommend", json={"books": {"id": "OL123W"}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)

    def test_recommendations_preserve_empty_and_catalog_error_responses(self):
        """Confirma os contratos de lista vazia e falha externa na recomendaÃ§Ã£o."""
        empty = self.post("/api/recommend", json={"books": []})
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json["books"], [])
        self.add_fixture_book()
        mine = [{"id": "OL123W", "subjects": ["Fantasy"]}]
        with patch.object(recomendacoes, "search_books", side_effect=catalogo.CatalogError("offline")):
            failed = self.post("/api/recommend", json={"books": mine})
        self.assertEqual(failed.status_code, 503)
        self.assertIn("error", failed.json)

    def test_recommendations_success_contract_is_preserved(self):
        """Confirma resposta de recomendaÃ§Ãµes com campos esperados pelo frontend."""
        self.add_fixture_book()
        mine = [{"id": "OL123W", "subjects": ["Fantasy"]}]
        other = {"id": "OL456W", "title": "Outra obra", "author": "Autoria", "subjects": ["Fantasy"]}
        with patch.object(recomendacoes, "search_books", return_value=(other,)):
            response = self.post("/api/recommend", json={"books": mine})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["books"][0]["id"], "OL456W")
        self.assertIn("subjects", response.json)

    def test_manual_search_external_error_returns_service_unavailable(self):
        """Confirma status 503 e JSON de erro para falha de catÃ¡logo na busca."""
        with patch("backend.routes.search_books", side_effect=catalogo.CatalogError("offline")):
            response = self.client.get("/api/search?q=livro")
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json)

    def test_manual_search_success_contract_is_preserved(self):
        """Confirma a resposta de busca manual consumida pelo JavaScript."""
        stub = ({"id": "OL123W", "title": "O Hobbit", "author": "Tolkien", "subjects": []},)
        with patch("backend.routes.search_books", return_value=stub):
            response = self.client.get("/api/search?q=O%20Hobbit")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["books"][0]["id"], "OL123W")

    def test_private_routes_require_login(self):
        """Confirma que as APIs e a biblioteca rejeitam sessões anônimas."""
        anonymous = entrypoint.app.test_client()
        self.assertEqual(anonymous.get("/").status_code, 302)
        self.assertEqual(anonymous.get("/api/library").status_code, 401)
        self.assertEqual(anonymous.get("/api/search?q=livro").status_code, 401)

    def test_normalization_and_work_key(self):
        """Confirma normalizaÃ§Ã£o de acentos e validaÃ§Ã£o de identificadores."""
        self.assertEqual(catalogo.normalize_text("A A\u00c7\u00c3O!"), "a acao")
        self.assertEqual(catalogo.canonical_key("/works/OL1234W"), "OL1234W")
        self.assertIsNone(catalogo.canonical_key("oops"))


if __name__ == "__main__":
    unittest.main()
