"""Valida telas e o fluxo autenticado em Edge usando somente a base de testes."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from PIL import Image
from playwright.sync_api import sync_playwright
from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["BIBLIOTECA_DATABASE_NAME"] = "biblioteca_inteligente_test"

from backend.database import session_scope  # noqa: E402
from backend.models import BibliotecaUsuario, Livro, ProgressoLeitura, Usuario  # noqa: E402


def limpar_conta_de_teste(nome_usuario: str, catalog_ids: list[str]) -> None:
    """Remove somente a conta criada pelo roteiro na base explicitamente isolada.

    Parâmetros:
        nome_usuario: identificador aleatório criado nesta execução.
        catalog_ids: chaves Open Library adicionadas nesta execução, mesmo quando
            a associação já foi removida pela interface.

    Retorno:
        Nenhum valor; os registros pessoais e livros sem outras associações
        são apagados em uma única transação da base `_test`.

    Integração:
        Usa as entidades SQLAlchemy e `session_scope` da camada já existente.

    Tratamento de erros:
        O erro é propagado para que a execução não declare limpeza concluída.
    """
    with session_scope() as db:
        account = db.scalar(select(Usuario).where(Usuario.nome_usuario == nome_usuario))
        if account is None:
            return
        book_ids = list(db.scalars(select(BibliotecaUsuario.livro_id).where(
            BibliotecaUsuario.usuario_id == account.id)))
        association_ids = select(BibliotecaUsuario.id).where(BibliotecaUsuario.usuario_id == account.id)
        db.execute(delete(ProgressoLeitura).where(ProgressoLeitura.biblioteca_usuario_id.in_(association_ids)))
        db.execute(delete(BibliotecaUsuario).where(BibliotecaUsuario.usuario_id == account.id))
        if book_ids:
            db.execute(delete(Livro).where(Livro.id.in_(book_ids), ~Livro.itens_biblioteca.any()))
        if catalog_ids:
            db.execute(delete(Livro).where(
                Livro.origem_catalogo == "openlibrary",
                Livro.identificador_externo.in_(catalog_ids),
                ~Livro.itens_biblioteca.any(),
            ))
        db.delete(account)


def main() -> int:
    """Executa cadastro, login, pesquisa real, persistência e inspeção visual.

    Retorno:
        Código zero quando as verificações terminam; erro em qualquer quebra.

    Integração:
        Playwright controla o Edge já instalado e consulta o Flask local em
        `127.0.0.1:5000`; imagens de evidência vão para `docs/evidencias`.

    Tratamento de erros:
        A limpeza da conta descartável é tentada mesmo quando a navegação falha.
    """
    username = f"ui_{uuid4().hex[:14]}"
    password = f"teste-{uuid4().hex}-Seguro"
    created_catalog_ids: list[str] = []
    evidence = ROOT / "docs" / "evidencias"
    evidence.mkdir(parents=True, exist_ok=True)
    evidence_prefix = os.environ.get("BIBLIOTECA_EVIDENCE_PREFIX", "etapa5")
    if evidence_prefix not in {"etapa5", "etapa6", "etapa7"}:
        raise ValueError("O prefixo de evidências não corresponde a uma etapa permitida.")
    test_cover = ROOT / "runtime" / f"{evidence_prefix}-capa-hobbit.png"
    source_cover = ROOT / "docs" / "evidencias" / "resultado-ocr-final.png"
    with Image.open(source_cover) as screenshot:
        screenshot.crop((420, 580, 532, 766)).convert("RGB").save(test_cover, format="PNG")
    executable = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not executable.is_file():
        raise RuntimeError("O navegador Edge instalado não foi encontrado para a inspeção.")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(executable), headless=True)
            context = browser.new_context(viewport={"width": 1365, "height": 900})
            context.add_init_script(
                "localStorage.setItem('estante-livros-v1', "
                "'[ {\"id\":\"registro-legado-teste\",\"title\":\"Registro legado preservado\"} ]');"
            )
            page = context.new_page()
            page.goto("http://127.0.0.1:5000/cadastro", wait_until="domcontentloaded")
            assert page.get_by_label("Nome de exibição").count() == 1
            page.screenshot(path=str(evidence / f"{evidence_prefix}-cadastro.png"), full_page=True)
            page.get_by_label("Nome de exibição").fill("Conta Visual de Teste")
            page.get_by_label("Nome de usuário").fill(username)
            page.get_by_label("Senha", exact=True).fill(password)
            confirmation = page.get_by_label("Confirmação de senha")
            confirmation.fill(password + "divergente")
            assert confirmation.evaluate("campo => !campo.validity.valid")
            confirmation.fill(password)
            page.get_by_role("button", name="Criar conta").click()
            page.wait_for_url("**/login?cadastro=concluido")
            page.screenshot(path=str(evidence / f"{evidence_prefix}-login.png"), full_page=True)
            page.get_by_label("Nome de usuário").fill(username)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Entrar").click()
            page.wait_for_url("http://127.0.0.1:5000/")
            page.get_by_text("Conta: Conta Visual de Teste").wait_for()
            page.locator("#legacy-notice").wait_for(state="visible")
            legacy_data = page.evaluate("localStorage.getItem('estante-livros-v1')")
            page.set_input_files("#image-input", str(test_cover))
            page.locator("#recognize-btn").click()
            page.locator("#ocr-text").wait_for(state="visible", timeout=60000)
            ocr_text = page.locator("#ocr-text").inner_text()
            assert "HOBBIT" in ocr_text.upper()
            ocr_candidate = page.locator(".book-item").filter(has_text="The Hobbit").first
            candidate_from_ocr = ocr_candidate.count() > 0
            if not candidate_from_ocr:
                # A busca manual permanece como recuperação quando o catálogo falha.
                page.get_by_label("Buscar livro pelo título").fill("The Hobbit")
                page.get_by_role("button", name="Buscar").click()
            page.get_by_text("The Hobbit", exact=True).first.wait_for(timeout=30000)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            page.screenshot(path=str(evidence / f"{evidence_prefix}-biblioteca-notebook.png"), full_page=True)
            candidate = page.locator(".book-item").filter(has_text="The Hobbit").first
            candidate.get_by_role("button", name="+ Adicionar").click()
            page.wait_for_function("""() => [...document.querySelectorAll('#library-books .book-title')]
                .some(element => element.textContent.trim() === 'The Hobbit')""")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("""() => [...document.querySelectorAll('#library-books .book-title')]
                .some(element => element.textContent.trim() === 'The Hobbit')""")
            assert page.evaluate("localStorage.getItem('estante-livros-v1')") == legacy_data
            page.locator("#recommend-btn").click()
            page.wait_for_function(
                "document.querySelector('#recommend-status').textContent !== "
                "'Buscando livros com temas parecidos...'"
            )
            assert "error" not in (page.locator("#recommend-status").get_attribute("class") or "")
            page.set_viewport_size({"width": 390, "height": 844})
            mobile_widths = page.evaluate("""() => ({
                viewport: window.innerWidth,
                document: document.documentElement.scrollWidth,
                page: (() => { const element = document.querySelector('.page');
                    const rect = element.getBoundingClientRect();
                    return {left: rect.left, right: rect.right, width: rect.width,
                        scrollWidth: element.scrollWidth}; })(),
                layout: (() => { const element = document.querySelector('.layout');
                    const rect = element.getBoundingClientRect();
                    return {left: rect.left, right: rect.right, width: rect.width,
                        scrollWidth: element.scrollWidth}; })(),
                offenders: [...document.querySelectorAll('body *')]
                    .map(element => ({tag: element.tagName, id: element.id,
                        className: typeof element.className === 'string' ? element.className : '',
                        left: Math.floor(element.getBoundingClientRect().left),
                        right: Math.ceil(element.getBoundingClientRect().right)}))
                    .filter(element => element.right > window.innerWidth + 1)
                    .slice(0, 10)
            })""")
            page.screenshot(path=str(evidence / f"{evidence_prefix}-biblioteca-celular.png"), full_page=True)
            assert mobile_widths["document"] <= mobile_widths["viewport"] + 1, mobile_widths
            library_snapshot = page.evaluate("async () => (await fetch('/api/library')).json()")
            created_catalog_ids.extend(book["catalog_id"] for book in library_snapshot["books"]
                                       if isinstance(book.get("catalog_id"), str))
            page.get_by_role("button", name="Sair").click()
            page.wait_for_url("**/login")
            page.get_by_label("Nome de usuário").fill(username)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Entrar").click()
            page.wait_for_url("http://127.0.0.1:5000/")
            page.get_by_text("The Hobbit", exact=True).last.wait_for()
            page.locator(".remove-btn").last.click()
            page.get_by_text("The Hobbit", exact=True).wait_for(state="detached")
            print(
                "Edge validou OCR real, "
                + ("candidato OCR" if candidate_from_ocr else "recuperação por busca manual")
                + ", persistência, logout, novo login, remoção e dois tamanhos de tela."
            )
            context.close()
            browser.close()
    finally:
        try:
            limpar_conta_de_teste(username, created_catalog_ids)
        finally:
            test_cover.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
