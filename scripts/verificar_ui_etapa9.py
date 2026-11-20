"""Valida gestão da biblioteca e o fluxo autenticado em Edge na base de testes."""

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
from backend.models import BibliotecaUsuario, Livro, MetaLeitura, Preferencia, ProgressoLeitura, Usuario  # noqa: E402


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
        db.execute(delete(MetaLeitura).where(MetaLeitura.usuario_id == account.id))
        db.execute(delete(Preferencia).where(Preferencia.usuario_id == account.id))
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
    evidence_prefix = os.environ.get("BIBLIOTECA_EVIDENCE_PREFIX", "etapa9")
    if evidence_prefix not in {"etapa9"}:
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
            page.goto("http://127.0.0.1:5000/sobre-ods", wait_until="domcontentloaded")
            assert page.get_by_role("heading", name="Ponto de partida: as ODS").count() == 1
            assert page.locator(".ods-questions li").count() == 4
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            page.screenshot(path=str(evidence / f"{evidence_prefix}-ods-notebook.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            page.screenshot(path=str(evidence / f"{evidence_prefix}-ods-celular.png"), full_page=True)
            page.set_viewport_size({"width": 1365, "height": 900})
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

            seed_ids = [f"OL{uuid4().int % 900000000 + 100000000}W" for _ in range(12)]
            seed_result = page.evaluate("""async (ids) => {
                const token = document.querySelector('meta[name="csrf-token"]').content;
                const results = [];
                for (const [index, catalog_id] of ids.entries()) {
                    const payload = {catalog_id, title: `Café E2E ${String(index).padStart(2, '0')}`,
                        author: 'Ágata E2E', subjects: ['Fantasia'], year: 2020 + index,
                        metadata: index === 0 ? {isbn_13: '9780306406157',
                            metadata_sources: {isbn_13: 'openlibrary'}, metadata_scope: 'work'} : {}};
                    const response = await fetch('/api/library', {method: 'POST',
                        headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
                        body: JSON.stringify(payload)});
                    results.push(response.status);
                }
                return results;
            }""", seed_ids)
            assert seed_result == [201] * 12, seed_result
            page.reload(wait_until="domcontentloaded")
            page.get_by_text("13 livros", exact=True).wait_for()

            page.locator("#library-query").fill("cafe e2e 00")
            page.locator("#library-author").fill("agata")
            page.locator("#library-subject").fill("fantasia")
            page.wait_for_function("document.querySelector('#library-summary').textContent.includes('1 nesta consulta')")
            filtered = page.locator("#library-books .saved-book")
            assert filtered.count() == 1
            seed_card = filtered.first
            seed_card.locator(".favorite-toggle").click()
            page.get_by_text("Livro marcado como favorito.").wait_for()
            page.locator("#favorites-only").check()
            assert filtered.count() == 1
            seed_card.get_by_role("button", name="Detalhes").click()
            page.locator("#book-details-dialog[open]").wait_for()
            assert page.locator("#details-content").inner_text().find("Fantasia") >= 0
            page.locator("#personal-notes").fill("Nota privada <script>alert(1)</script>")
            page.get_by_role("button", name="Salvar observações").click()
            page.get_by_text("Observações salvas nesta conta.").wait_for()
            assert page.locator("#details-content script").count() == 0
            saved_note = page.evaluate("""async () => {
                const response = await fetch('/api/library?q=cafe%20e2e%2000&author=agata&subject=fantasia&favorites=true');
                const data = await response.json();
                return {status: response.status, notes: data.books?.[0]?.notes};
            }""")
            assert saved_note == {"status": 200, "notes": "Nota privada <script>alert(1)</script>"}, saved_note
            page.locator("#progress-status").select_option("lendo")
            page.locator("#progress-pages-read").fill("24")
            page.locator("#progress-total-pages").fill("120")
            page.locator("#progress-started").fill("2026-11-10")
            page.get_by_role("button", name="Salvar progresso").click()
            page.get_by_text("Progresso salvo nesta conta.").wait_for()
            page.locator("#progress-status").select_option("concluido")
            page.locator("#progress-completed").fill("2026-11-19")
            page.get_by_role("button", name="Salvar progresso").click()
            page.wait_for_function("document.querySelector('#progress-summary').textContent.includes('100%')")
            page.get_by_role("button", name="Fechar detalhes").click()
            page.locator("#goal-target").fill("3")
            page.locator("#goal-start").fill("2026-11-01")
            page.locator("#goal-end").fill("2026-11-30")
            page.get_by_role("button", name="Criar meta").click()
            page.locator("#goals-list").get_by_text("1 de 3 livros concluídos").wait_for()
            page.locator("#preference-category").select_option("assunto")
            page.locator("#preference-value").fill("Fantasia")
            page.locator("#preference-level").select_option("4")
            page.get_by_role("button", name="Salvar interesse").click()
            page.locator("#preferences-list").get_by_text("Fantasia").wait_for()
            page.reload(wait_until="domcontentloaded")
            page.locator("#library-query").fill("cafe e2e 00")
            page.locator("#library-author").fill("agata")
            page.locator("#library-subject").fill("fantasia")
            page.locator("#favorites-only").check()
            page.wait_for_function("document.querySelector('#library-summary').textContent.includes('1 nesta consulta')")
            filtered = page.locator("#library-books .saved-book")
            assert filtered.count() == 1
            filtered.first.get_by_role("button", name="Detalhes").click()
            page.wait_for_function("document.querySelector('#personal-notes').value === "
                                   "'Nota privada <script>alert(1)</script>'")
            assert page.get_by_role("button", name="Remover Café E2E 00 dos favoritos").count() == 1
            page.get_by_role("button", name="Fechar detalhes").click()
            page.get_by_role("button", name="Limpar filtros").click()
            page.wait_for_function("document.querySelector('#library-summary').textContent.includes('13 nesta consulta')")
            page.locator("#library-query").fill("978-0-306-40615-7")
            page.wait_for_function("document.querySelector('#library-summary').textContent.includes('1 nesta consulta')")
            isbn_result = page.locator("#library-books .saved-book")
            assert isbn_result.count() == 1
            assert "Café E2E 00" in isbn_result.first.inner_text()
            page.get_by_role("button", name="Limpar filtros").click()
            page.wait_for_function("document.querySelector('#library-summary').textContent.includes('13 nesta consulta')")
            page.get_by_label("Ordenar por").select_option("titulo_asc")
            page.wait_for_function("""() => document.querySelector('#library-books .book-title')
                ?.textContent.trim() === 'Café E2E 00'""")
            assert page.locator("#library-pagination").is_visible()
            assert page.locator("#library-page-label").inner_text() == "Página 1 de 2"
            page.screenshot(path=str(evidence / f"{evidence_prefix}-biblioteca-notebook.png"), full_page=True)
            page.get_by_role("button", name="Próxima").click()
            page.wait_for_function("document.querySelector('#library-page-label').textContent === 'Página 2 de 2'")
            assert page.locator("#library-books .saved-book").count() == 1
            page.get_by_role("button", name="Anterior").click()

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
            page.locator("#library-query").fill("The Hobbit")
            hobbit_card = page.locator("#library-books .saved-book").filter(has_text="The Hobbit")
            hobbit_card.wait_for()
            page.once("dialog", lambda dialog: dialog.accept())
            hobbit_card.get_by_role("button", name="Remover").click()
            page.wait_for_function("""() => ![...document.querySelectorAll('#library-books .book-title')]
                .some(element => element.textContent.trim() === 'The Hobbit')""")
            print(
                "Edge validou OCR real, "
                + ("candidato OCR" if candidate_from_ocr else "recuperação por busca manual")
                + ", pesquisa pessoal, filtros, ordenação, páginas, detalhes, favorito, observação, "
                  "progresso, meta, interesse, persistência, isolamento e dois tamanhos de tela."
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
