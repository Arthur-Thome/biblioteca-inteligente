"""Rotas HTTP e adaptação dos serviços à interface web."""

import logging
import os
import re
import threading
import time
import unicodedata
from datetime import date, datetime, time as datetime_time, timezone
from functools import wraps
from typing import Any
from uuid import UUID

from flask import Blueprint, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from backend.catalogo import CatalogError, normalize_isbn, search_books
from backend.database import session_scope
from backend.repositories.biblioteca import (
    adicionar_livro,
    atualizar_dados_pessoais,
    listar_livros_usuario,
    listar_pagina_usuario,
    obter_item_usuario,
    remover_livro_usuario,
)
from backend.repositories.progresso import STATUS_VALIDOS, obter_progresso, salvar_progresso
from backend.repositories.metas import (
    atualizar_meta,
    contar_livros_concluidos,
    criar_meta,
    listar_metas,
    remover_meta,
)
from backend.repositories.preferencias import (
    criar_preferencia,
    listar_preferencias,
    remover_preferencia,
)
from backend.repositories.livros import criar_livro, obter_por_catalogo
from backend.repositories.usuarios import criar_usuario, obter_usuario_por_nome
from backend.recomendacoes import recommend_books
from backend.validacoes import valid_books, validate_image_bytes
from backend.visao_computacional import (
    MIN_OCR_MATCH_SCORE,
    author_match_strength,
    author_matches_ocr,
    extract_cover_text,
    get_ocr_engine,
    score_ocr_match,
    suggest_search_queries,
)

LOGGER = logging.getLogger(__name__)
api = Blueprint("api", __name__)
LOGIN_FAILURES: dict[str, list[float]] = {}
LOGIN_FAILURES_LOCK = threading.Lock()
LOGIN_WINDOW_SECONDS = 600
LOGIN_MAX_FAILURES = 8


@api.get("/sobre-ods")
def sobre_ods():
    """Apresenta ao público a justificativa acadêmica e os limites da ODS.

    Retorno:
        Template público independente de autenticação.

    Integração:
        O menu principal e os formulários de conta apontam para esta rota.

    Tratamento de erros:
        A página é estática e não consulta banco nem serviço externo.
    """
    return render_template("sobre_ods.html")


def _autenticado_json(function):
    """Restringe uma API a uma sessão cuja conta já foi conferida no PostgreSQL.

    Parâmetros:
        function: função de rota protegida.

    Retorno:
        Função decorada que devolve HTTP 401 quando a sessão não possui usuário.
    """
    @wraps(function)
    def wrapped(*args, **kwargs):
        """Exige usuário validado antes de executar a função de rota decorada."""
        if g.get("usuario") is None:
            return jsonify({"error": "A sessão expirou. Entre novamente."}), 401
        return function(*args, **kwargs)
    return wrapped


def _normalizar_usuario(value: Any) -> str:
    """Padroniza nome de usuário Unicode e rejeita caracteres não previstos.

    Parâmetros:
        value: dado bruto submetido pelo formulário.

    Retorno:
        Nome em minúsculas, sem espaços laterais e com espaços internos reduzidos.
    """
    if not isinstance(value, str):
        return ""
    return unicodedata.normalize("NFKC", " ".join(value.split())).casefold()


def _validar_senha(value: Any) -> str | None:
    """Aplica limites de comprimento sem expor a senha em respostas ou logs.

    Parâmetros:
        value: senha submetida pelo formulário.

    Retorno:
        Mensagem de validação ou `None` quando o comprimento é aceitável.
    """
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        return "A senha deve possuir entre 12 e 128 caracteres."
    return None


def _rate_limited(key: str) -> bool:
    """Limita temporariamente tentativas consecutivas por endereço e usuário.

    Parâmetros:
        key: identificador opaco formado a partir do endereço e usuário canônico.

    Retorno:
        `True` quando o limite temporário foi atingido.
    """
    now = time.monotonic()
    with LOGIN_FAILURES_LOCK:
        for expired_key in [entry for entry, stamps in LOGIN_FAILURES.items()
                            if not any(now - stamp < LOGIN_WINDOW_SECONDS for stamp in stamps)]:
            LOGIN_FAILURES.pop(expired_key, None)
        attempts = [stamp for stamp in LOGIN_FAILURES.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        LOGIN_FAILURES[key] = attempts
        return len(attempts) >= LOGIN_MAX_FAILURES


def _record_login_failure(key: str, *, success: bool = False) -> None:
    """Atualiza o contador em memória e remove contadores após login válido.

    Parâmetros:
        key: identificador opaco da combinação endereço e usuário.
        success: indica se as credenciais foram aceitas.
    """
    now = time.monotonic()
    with LOGIN_FAILURES_LOCK:
        if success:
            LOGIN_FAILURES.pop(key, None)
        else:
            previous = [stamp for stamp in LOGIN_FAILURES.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
            previous.append(now)
            LOGIN_FAILURES[key] = previous


def _parse_date_value(value: Any, field_name: str, *, required: bool = False) -> datetime | None:
    """Converte data ISO do formulário em meia-noite UTC validada.

    Parâmetros:
        value: valor recebido no JSON, normalmente texto `AAAA-MM-DD`.
        field_name: nome interno usado para compor uma mensagem controlada.
        required: indica se o campo deve conter uma data.

    Retorno:
        Timestamp timezone-aware em UTC ou `None` para data opcional vazia.

    Integração:
        Rotas de progresso convertem datas HTML antes de chamar o repositório.

    Tratamento de erros:
        Tipos e datas impossíveis geram `ValueError` sem expor detalhes SQL.
    """
    if value in (None, "") and not required:
        return None
    if not isinstance(value, str):
        raise ValueError(f"A data {field_name} é inválida.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"A data {field_name} é inválida.") from error
    if parsed.isoformat() != value:
        raise ValueError(f"A data {field_name} é inválida.")
    return datetime.combine(parsed, datetime_time.min, tzinfo=timezone.utc)


def _serialize_progress(record, *, fallback_total: int | None = None) -> dict[str, Any]:
    """Expõe progresso com percentual calculado, sem chamar o valor de certeza.

    Parâmetros:
        record: progresso persistido ou `None` quando ainda não foi criado.
        fallback_total: total bibliográfico usado somente se o registro não o tem.

    Retorno:
        Dicionário JSON estável para o formulário de acompanhamento.

    Integração:
        GET da biblioteca/detalhes e GET de progresso enviam esta estrutura.

    Tratamento de erros:
        Totais ausentes ou não positivos não produzem percentual.
    """
    if not isinstance(fallback_total, int) or isinstance(fallback_total, bool) or fallback_total <= 0:
        fallback_total = None
    total = (record.total_paginas if record else None) or fallback_total
    read = record.paginas_lidas if record else 0
    percent = min(100, round(read * 100 / total)) if total and total > 0 else None
    return {
        "status": record.status if record else "nao_iniciado",
        "pages_read": read,
        "total_pages": total,
        "progress_percent": percent,
        "started_at": record.iniciado_em.date().isoformat() if record and record.iniciado_em else "",
        "completed_at": record.concluido_em.date().isoformat() if record and record.concluido_em else "",
        "notes": record.observacoes if record else None,
    }


def _serialize_goal(db, goal, *, usuario_id: UUID) -> dict[str, Any]:
    """Calcula o progresso de uma meta a partir de conclusões do proprietário.

    Parâmetros:
        db: sessão SQLAlchemy ativa.
        goal: meta já filtrada para a conta autenticada.
        usuario_id: proprietário obtido da sessão Flask.

    Retorno:
        Meta com quantidade concluída, restante e percentual limitado a 100.

    Integração:
        A API de metas utiliza contagem distinta de livros concluídos no período.

    Tratamento de erros:
        A consulta de contagem falha junto da transação e vira resposta controlada.
    """
    completed = contar_livros_concluidos(
        db, usuario_id=usuario_id,
        periodo_inicio=goal.periodo_inicio,
        periodo_fim=goal.periodo_fim,
    )
    target = goal.quantidade_objetivo
    return {
        "id": str(goal.id),
        "target": target,
        "start_date": goal.periodo_inicio.isoformat(),
        "end_date": goal.periodo_fim.isoformat(),
        "completed": completed,
        "remaining": max(0, target - completed),
        "progress_percent": min(100, round(completed * 100 / target)),
    }


def _read_goal_input(payload: Any) -> tuple[int, date, date]:
    """Valida quantidade e intervalo de uma meta recebida como JSON.

    Parâmetros:
        payload: objeto JSON enviado pela interface.

    Retorno:
        Quantidade-alvo e datas inclusivas validadas.

    Integração:
        POST e PUT das metas usam a mesma regra antes de chamar o repositório.

    Tratamento de erros:
        Campos ausentes, booleanos, formatos impossíveis ou período invertido
        geram `ValueError` e resposta HTTP 400.
    """
    if not isinstance(payload, dict) or set(payload) != {"target", "start_date", "end_date"}:
        raise ValueError("Informe objetivo, data inicial e data final.")
    target = payload["target"]
    if not isinstance(target, int) or isinstance(target, bool) or not 1 <= target <= 500:
        raise ValueError("O objetivo deve ser um número inteiro entre 1 e 500 livros.")
    start = payload["start_date"]
    end = payload["end_date"]
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError("As datas da meta são obrigatórias.")
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as error:
        raise ValueError("Uma das datas da meta é impossível.") from error
    if start_date.isoformat() != start or end_date.isoformat() != end or end_date <= start_date:
        raise ValueError("A data final deve ser posterior à data inicial.")
    if (end_date - start_date).days > 3660:
        raise ValueError("O período da meta não pode ultrapassar dez anos.")
    return target, start_date, end_date


@api.get("/cadastro")
def cadastro():
    """Apresenta o formulário público para criação de uma conta PostgreSQL.

    Retorno:
        Página de cadastro ou redirecionamento para a biblioteca autenticada.
    """
    if g.get("usuario"):
        return redirect(url_for("api.home"))
    return render_template("cadastro.html", erro=None, nome="", nome_usuario="")


@api.post("/cadastro")
def cadastrar():
    """Valida campos e grava conta com hash Werkzeug na tabela usuarios.

    Retorno:
        Redirecionamento ao login após cadastro, ou formulário com erro claro.

    Integração:
        A rota usa `criar_usuario` e session_scope; o formulário inclui CSRF.

    Tratamento de erros:
        Conflito de username recebe mensagem neutra e indisponibilidade do
        banco retorna uma mensagem controlada sem detalhes SQL.
    """
    nome = request.form.get("nome", "").strip()
    nome_usuario = _normalizar_usuario(request.form.get("nome_usuario", ""))
    senha = request.form.get("senha", "")
    confirmacao = request.form.get("confirmacao", "")
    erro = None
    if not nome or len(nome) > 160 or re.search(r"[\x00-\x1f\x7f]", nome):
        erro = "Informe um nome de exibição com até 160 caracteres."
    elif not re.fullmatch(r"[\w.-]{3,40}", nome_usuario, flags=re.UNICODE):
        erro = "O nome de usuário deve ter de 3 a 40 letras, números, pontos, hífens ou sublinhados."
    elif (erro := _validar_senha(senha)):
        pass
    elif senha != confirmacao:
        erro = "A senha e a confirmação precisam corresponder."
    if erro:
        return render_template("cadastro.html", erro=erro, nome=nome, nome_usuario=nome_usuario), 400
    try:
        password_hash = generate_password_hash(senha, method="scrypt")
        with session_scope() as db:
            criar_usuario(db, nome=nome, nome_usuario=nome_usuario, senha_hash=password_hash)
    except IntegrityError:
        erro = "Não foi possível criar a conta com esses dados. Verifique o nome de usuário."
        return render_template("cadastro.html", erro=erro, nome=nome, nome_usuario=nome_usuario), 409
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao salvar cadastro (%s).", type(error).__name__)
        erro = "O banco de dados está indisponível. Tente novamente."
        return render_template("cadastro.html", erro=erro, nome=nome, nome_usuario=nome_usuario), 503
    return redirect(url_for("api.login", cadastro="concluido"))


@api.get("/login")
def login():
    """Apresenta a tela pública de entrada na conta.

    Retorno:
        Página de login com mensagem opcional após cadastro concluído.
    """
    if g.get("usuario"):
        return redirect(url_for("api.home"))
    mensagem = "Conta criada. A sessão pode ser iniciada." if request.args.get("cadastro") == "concluido" else None
    return render_template("login.html", erro=None, mensagem=mensagem, nome_usuario="")


@api.post("/login")
def entrar():
    """Confere o hash de senha e inicia sessão com UUID mínimo e CSRF renovado.

    Retorno:
        Redirecionamento para a biblioteca ou formulário com mensagem genérica.

    Tratamento de erros:
        Credenciais inválidas não revelam se o nome existe; erro PostgreSQL
        recebe HTTP 503 sem texto técnico.
    """
    nome_usuario = _normalizar_usuario(request.form.get("nome_usuario", ""))
    senha = request.form.get("senha", "")
    key = f"{request.remote_addr or 'local'}:{nome_usuario[:40] or 'vazio'}"
    if _rate_limited(key):
        return render_template(
            "login.html",
            erro="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
            mensagem=None,
            nome_usuario=nome_usuario,
        ), 429
    if (not re.fullmatch(r"[\w.-]{3,40}", nome_usuario, flags=re.UNICODE)
            or not isinstance(senha, str) or len(senha) > 128):
        _record_login_failure(key)
        return render_template(
            "login.html", erro="Nome de usuário ou senha inválidos.", mensagem=None, nome_usuario=""
        ), 401
    try:
        with session_scope() as db:
            usuario = obter_usuario_por_nome(db, nome_usuario) if nome_usuario else None
            valid = bool(usuario and check_password_hash(usuario.senha_hash, senha))
            user_id = str(usuario.id) if valid else None
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao verificar login (%s).", type(error).__name__)
        return render_template(
            "login.html",
            erro="O banco de dados está indisponível. Tente novamente.",
            mensagem=None,
            nome_usuario=nome_usuario,
        ), 503
    if not valid:
        _record_login_failure(key)
        return render_template(
            "login.html", erro="Nome de usuário ou senha inválidos.", mensagem=None, nome_usuario=nome_usuario
        ), 401
    _record_login_failure(key, success=True)
    session.clear()
    from secrets import token_urlsafe

    session.update(usuario_id=user_id, csrf_token=token_urlsafe(32), _permanent=True)
    return redirect(url_for("api.home"))


@api.post("/logout")
def logout():
    """Encerra sessão autenticada após validar proteção CSRF.

    Retorno:
        Redirecionamento à tela de login após remoção de todo estado da sessão.
    """
    session.clear()
    return redirect(url_for("api.login"))


@api.get("/")
def home():
    """Entrega o template principal que carrega CSS e JavaScript estáticos.

    Retorno:
        Resposta HTML renderizada pelo mecanismo de templates do Flask.

    Integração:
        O documento utiliza os diretórios ``templates`` e ``static`` do projeto.

    Tratamento de erros:
        Erros de renderização são tratados pelo mecanismo padrão do Flask.
    """
    if g.get("usuario") is None:
        return redirect(url_for("api.login"))
    return render_template("index.html", usuario=g.usuario)


@api.get("/api/health")
def health():
    """Informa os componentes previstos pelo protótipo sem executar dependências.

    Retorno:
        JSON com estado da aplicação e nomes do OCR e catálogo configurados.

    Integração:
        O navegador ou uma verificação local pode consultar esta rota.

    Tratamento de erros:
        A resposta não confirma disponibilidade de internet nem inicialização
        dos modelos; ela apenas identifica os serviços configurados.
    """
    return jsonify({"status": "ok", "ocr": "RapidOCR", "catalog": "Open Library"})


@api.get("/api/search")
@_autenticado_json
def search():
    """Pesquisa livros manualmente a partir da consulta enviada pela interface.

    Retorno:
        JSON com ``books`` ou ``error`` e status HTTP correspondente.

    Integração:
        Recebe ``q`` e ``type`` por query string e chama ``search_books`` no catálogo.

    Tratamento de erros:
        Consulta curta retorna 400; indisponibilidade da Open Library retorna 503.
    """
    query = (request.args.get("q") or "").strip()
    search_type = (request.args.get("type") or "title").strip().lower()
    if len(query) < 2:
        return jsonify({"error": "Digite ao menos duas letras."}), 400
    if search_type not in {"title", "author", "isbn"}:
        return jsonify({"error": "Escolha uma busca por título, autor ou ISBN."}), 400
    try:
        return jsonify({"books": search_books(query, 10, search_type=search_type)})
    except CatalogError as exc:
        response = jsonify({"error": str(exc)})
        if exc.retry_after:
            response.headers["Retry-After"] = exc.retry_after
        return response, 503


@api.post("/api/recognize")
@_autenticado_json
def recognize():
    """Valida uma imagem, executa OCR e busca candidatos no catálogo.

    Retorno:
        JSON com textos reconhecidos, candidatos, consultas e mensagem opcional.

    Integração:
        Recebe multipart ``image``, chama o serviço RapidOCR e consulta Open
        Library antes de enviar resultados ao JavaScript.

    Tratamento de erros:
        Ausência, bytes vazios ou imagem inválida retornam 400; falha do OCR
        retorna 500 genérico; falha do catálogo é comunicada sem descartar o
        texto reconhecido.
    """
    uploaded = request.files.get("image")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Selecione uma foto da capa."}), 400
    data = uploaded.read()
    if not data:
        return jsonify({"error": "A imagem enviada está vazia."}), 400
    if not validate_image_bytes(data):
        return jsonify({"error": "Arquivo inválido. Escolha uma imagem JPG, PNG ou WEBP."}), 400

    try:
        get_ocr_engine()
        entries = extract_cover_text(data)
    except Exception:
        LOGGER.exception("Falha durante a inicialização ou inferência do OCR")
        return jsonify({"error": "OCR indisponível. Tente reiniciar o programa; a busca manual ainda funciona."}), 500

    if not entries:
        return jsonify({
            "detected": [],
            "books": [],
            "message": "Não encontrei texto legível nessa foto. Tente aproximar a capa ou buscar o título manualmente.",
        })

    combined = " ".join(item["text"] for item in entries)
    catalog_candidates: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    retry_after = None
    queries = suggest_search_queries(entries)
    for query in queries:
        try:
            for book in search_books(query, 8):
                catalog_candidates.setdefault(book["id"], book)
        except CatalogError as error:
            problems.append(str(error))
            retry_after = error.retry_after
            break
    author_evidence = any(author_matches_ocr(book, combined) for book in catalog_candidates.values())
    merged = {}
    for book in catalog_candidates.values():
        score = score_ocr_match(book, combined, penalize_author_mismatch=author_evidence)
        if score >= MIN_OCR_MATCH_SCORE:
            merged[book["id"]] = {**book, "match": score}
    books = sorted(
        merged.values(),
        key=lambda book: (-book["match"], -author_match_strength(book, combined), book["title"]),
    )[:8]
    if problems:
        message = problems[0] + " O texto reconhecido ainda pode ser usado na busca manual."
    elif not books:
        message = "O texto foi reconhecido, mas não encontrei uma correspondência segura. Use a busca manual."
    else:
        message = None
    response = jsonify({"detected": entries, "books": books, "queries": queries, "message": message})
    if retry_after:
        response.headers["Retry-After"] = retry_after
    return response


@api.post("/api/recommend")
@_autenticado_json
def recommend():
    """Consulta livros da conta autenticada e retorna recomendações relacionadas.

    Retorno:
        JSON serializável com ``books``, ``subjects`` e mensagem opcional.

    Integração:
        Lê associações do PostgreSQL filtradas pelo UUID da sessão, valida os
        metadados e delega ao serviço que consulta Open Library.

    Tratamento de erros:
        O corpo JSON opcional com estrutura inválida retorna 400; erro no banco
        ou indisponibilidade do catálogo resulta em resposta controlada 503.
    """
    payload = request.get_json(silent=True)
    if payload is not None:
        if not isinstance(payload, dict):
            return jsonify({"error": "O corpo JSON deve ser um objeto."}), 400
        if "books" in payload and not isinstance(payload["books"], list):
            return jsonify({"error": "O campo books deve conter uma lista."}), 400
    elif request.data:
        return jsonify({"error": "Envie um objeto JSON válido."}), 400
    try:
        with session_scope() as db:
            entries = listar_livros_usuario(db, usuario_id=g.usuario.id)
            books = [{"id": entry.livro.identificador_externo or str(entry.livro.id),
                      "title": entry.livro.titulo,
                      "author": ", ".join(entry.livro.autores or []),
                      "subjects": entry.livro.assuntos or [],
                      "genres": entry.livro.generos or [],
                      "favorite": bool(entry.favorito)}
                     for entry in entries]
            preferences = [
                {"category": item.categoria, "value": item.valor, "level": item.nivel}
                for item in listar_preferencias(db, usuario_id=g.usuario.id)
            ]
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao obter livros para recomendação (%s).", type(error).__name__)
        return jsonify({"error": "A biblioteca está temporariamente indisponível."}), 503
    book_context = {item["id"]: item for item in books}
    books = valid_books(books)
    books = [
        {**item,
         "title": book_context.get(item["id"], {}).get("title", ""),
         "favorite": bool(book_context.get(item["id"], {}).get("favorite")),
         "genres": book_context.get(item["id"], {}).get("genres", [])}
        for item in books
    ]
    try:
        return jsonify(recommend_books(books, preferences=preferences))
    except CatalogError as exc:
        response = jsonify({"error": str(exc)})
        if exc.retry_after:
            response.headers["Retry-After"] = exc.retry_after
        return response, 503


@api.get("/api/library/<uuid:item_id>/progress")
@_autenticado_json
def library_progress_get(item_id: UUID):
    """Consulta progresso de leitura da associação pertencente à sessão.

    Parâmetros:
        item_id: UUID da associação pessoal, sem aceitar ID de usuário.

    Retorno:
        JSON com status, páginas, datas e percentual calculado ou HTTP 404.

    Integração:
        Consulta repositórios PostgreSQL e devolve valores para o diálogo do livro.

    Tratamento de erros:
        Falha do banco resulta em 503 sem detalhes de conexão.
    """
    try:
        with session_scope() as db:
            entry = obter_item_usuario(db, usuario_id=g.usuario.id, item_id=item_id)
            if entry is None:
                return jsonify({"error": "O livro não foi encontrado nesta biblioteca."}), 404
            metadata = entry.livro.metadados if isinstance(entry.livro.metadados, dict) else {}
            fallback_total = metadata.get("page_count")
            if not isinstance(fallback_total, int) or isinstance(fallback_total, bool) or fallback_total <= 0:
                fallback_total = None
            record = obter_progresso(db, usuario_id=g.usuario.id, item_id=item_id)
            return jsonify({"progress": _serialize_progress(record, fallback_total=fallback_total)})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao consultar progresso (%s).", type(error).__name__)
        return jsonify({"error": "O progresso está temporariamente indisponível."}), 503


@api.put("/api/library/<uuid:item_id>/progress")
@_autenticado_json
def library_progress_put(item_id: UUID):
    """Cria ou atualiza progresso com datas e páginas validadas.

    Parâmetros:
        item_id: UUID da associação pertencente à conta autenticada.

    Retorno:
        JSON do progresso salvo, HTTP 400 para campos inválidos e 404 para item alheio.

    Integração:
        PUT exige CSRF global, valida dados e chama `salvar_progresso`.

    Tratamento de erros:
        Datas futuras/invertidas, valores numéricos inválidos e estado inconsistente
        são rejeitados sem alterar a associação ou os metadados do livro.
    """
    payload = request.get_json(silent=True)
    allowed = {"status", "pages_read", "total_pages", "started_at", "completed_at"}
    if not isinstance(payload, dict) or set(payload) - allowed or "status" not in payload:
        return jsonify({"error": "Os dados de progresso são inválidos."}), 400
    status = payload.get("status")
    if not isinstance(status, str) or status not in STATUS_VALIDOS:
        return jsonify({"error": "Selecione um estado de leitura válido."}), 400
    pages_read = payload.get("pages_read", 0)
    total_pages = payload.get("total_pages")
    if (not isinstance(pages_read, int) or isinstance(pages_read, bool) or pages_read < 0
            or (total_pages is not None and (
                not isinstance(total_pages, int) or isinstance(total_pages, bool) or total_pages < 1
            ))):
        return jsonify({"error": "As páginas devem ser números inteiros não negativos."}), 400
    if total_pages is not None and pages_read > total_pages:
        return jsonify({"error": "As páginas lidas não podem superar o total conhecido."}), 400
    try:
        started = _parse_date_value(payload.get("started_at"), "de início")
        completed = _parse_date_value(payload.get("completed_at"), "de conclusão")
        now = datetime.now(timezone.utc)
        if any(value and value.date() > now.date() for value in (started, completed)):
            raise ValueError("As datas de leitura não podem estar no futuro.")
        if status == "lendo" and started is None:
            started = datetime.combine(now.date(), datetime_time.min, tzinfo=timezone.utc)
        if status == "concluido":
            completed = completed or datetime.combine(now.date(), datetime_time.min, tzinfo=timezone.utc)
            started = started or completed
            if total_pages is not None:
                pages_read = total_pages
        elif completed is not None:
            raise ValueError("A data de conclusão somente é válida no estado concluído.")
        if status == "nao_iniciado" and (pages_read > 0 or started is not None):
            raise ValueError("Um livro não iniciado não pode ter páginas ou data de início.")
        if started and completed and completed < started:
            raise ValueError("A conclusão não pode anteceder o início da leitura.")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_scope() as db:
            entry = obter_item_usuario(db, usuario_id=g.usuario.id, item_id=item_id)
            if entry is None:
                return jsonify({"error": "O livro não foi encontrado nesta biblioteca."}), 404
            metadata = entry.livro.metadados if isinstance(entry.livro.metadados, dict) else {}
            if "total_pages" not in payload:
                raw_total = metadata.get("page_count")
                total_pages = raw_total if isinstance(raw_total, int) and not isinstance(raw_total, bool) else None
            if total_pages is not None and pages_read > total_pages:
                return jsonify({"error": "As páginas lidas não podem superar o total conhecido."}), 400
            if status == "concluido" and total_pages is not None:
                pages_read = total_pages
            record = salvar_progresso(
                db, usuario_id=g.usuario.id, item_id=item_id, status=status,
                paginas_lidas=pages_read, total_paginas=total_pages,
                iniciado_em=started, concluido_em=completed,
            )
            result = _serialize_progress(record)
        return jsonify({"progress": result})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao salvar progresso (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível salvar o progresso agora."}), 503


@api.get("/api/goals")
@_autenticado_json
def goals_list():
    """Lista metas próprias com progresso derivado dos livros concluídos.

    Retorno:
        JSON contendo metas, quantidades concluídas, restantes e percentuais.

    Integração:
        A camada de repositório calcula conclusão distinta no período inclusivo.

    Tratamento de erros:
        Indisponibilidade PostgreSQL resulta em 503 sem detalhes internos.
    """
    try:
        with session_scope() as db:
            goals = [_serialize_goal(db, goal, usuario_id=g.usuario.id)
                     for goal in listar_metas(db, usuario_id=g.usuario.id)]
        return jsonify({"goals": goals})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao listar metas (%s).", type(error).__name__)
        return jsonify({"error": "As metas estão temporariamente indisponíveis."}), 503


@api.post("/api/goals")
@_autenticado_json
def goals_create():
    """Cria meta voluntária sem atribuir propriedade a partir do payload.

    Retorno:
        JSON da meta em sucesso, HTTP 400 em entrada inválida e 409 em duplicata.

    Integração:
        POST exige CSRF e usa o UUID da sessão para chamar `criar_meta`.

    Tratamento de erros:
        Conflito único de período recebe resposta controlada sem detalhe SQL.
    """
    try:
        target, start_date, end_date = _read_goal_input(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_scope() as db:
            goal = criar_meta(db, usuario_id=g.usuario.id, quantidade_objetivo=target,
                              periodo_inicio=start_date, periodo_fim=end_date)
            result = _serialize_goal(db, goal, usuario_id=g.usuario.id)
        return jsonify({"goal": result}), 201
    except IntegrityError:
        return jsonify({"error": "Já existe uma meta com este período."}), 409
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao criar meta (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível criar a meta agora."}), 503


@api.put("/api/goals/<uuid:goal_id>")
@_autenticado_json
def goals_update(goal_id: UUID):
    """Atualiza meta própria após validar objetivo e período inclusivo.

    Parâmetros:
        goal_id: UUID da meta; o dono sempre vem da sessão Flask.

    Retorno:
        JSON atualizado, HTTP 400 para dados inválidos, 404 para meta alheia.

    Integração:
        PUT exige CSRF e delega a atualização ao repositório de metas.

    Tratamento de erros:
        Conflito de período recebe 409 e falhas de banco recebem 503.
    """
    try:
        target, start_date, end_date = _read_goal_input(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    try:
        with session_scope() as db:
            goal = atualizar_meta(db, usuario_id=g.usuario.id, meta_id=goal_id,
                                  quantidade_objetivo=target, periodo_inicio=start_date,
                                  periodo_fim=end_date)
            if goal is None:
                return jsonify({"error": "A meta não foi encontrada nesta conta."}), 404
            result = _serialize_goal(db, goal, usuario_id=g.usuario.id)
        return jsonify({"goal": result})
    except IntegrityError:
        return jsonify({"error": "Já existe uma meta com este período."}), 409
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao atualizar meta (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível atualizar a meta agora."}), 503


@api.delete("/api/goals/<uuid:goal_id>")
@_autenticado_json
def goals_delete(goal_id: UUID):
    """Remove exclusivamente uma meta pertencente à sessão autenticada.

    Parâmetros:
        goal_id: UUID da meta solicitada.

    Retorno:
        JSON de confirmação ou HTTP 404 quando a meta não pertence à conta.

    Integração:
        DELETE exige CSRF e usa o filtro de proprietário no repositório.
    """
    try:
        with session_scope() as db:
            removed = remover_meta(db, usuario_id=g.usuario.id, meta_id=goal_id)
        if not removed:
            return jsonify({"error": "A meta não foi encontrada nesta conta."}), 404
        return jsonify({"status": "removida"})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao remover meta (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível remover a meta agora."}), 503


@api.get("/api/preferences")
@_autenticado_json
def preferences_list():
    """Lista preferências pessoais disponíveis para recomendações.

    Retorno:
        JSON com categoria, termo e intensidade das preferências próprias.

    Integração:
        A rota de recomendação consulta estes mesmos registros no PostgreSQL.
    """
    try:
        with session_scope() as db:
            values = [{"id": str(item.id), "category": item.categoria,
                       "value": item.valor, "level": item.nivel}
                      for item in listar_preferencias(db, usuario_id=g.usuario.id)]
        return jsonify({"preferences": values})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao consultar preferências (%s).", type(error).__name__)
        return jsonify({"error": "As preferências estão temporariamente indisponíveis."}), 503


@api.post("/api/preferences")
@_autenticado_json
def preferences_create():
    """Cria preferência pessoal validada para tema ou gênero.

    Retorno:
        JSON da preferência criada, HTTP 400 para payload inválido ou 409 duplicata.

    Integração:
        POST exige CSRF e relaciona o registro à conta obtida na sessão.
    """
    payload = request.get_json(silent=True)
    if (not isinstance(payload, dict) or set(payload) != {"category", "value", "level"}
            or payload.get("category") not in {"genero", "assunto"}
            or not isinstance(payload.get("value"), str)
            or not isinstance(payload.get("level"), int)
            or isinstance(payload.get("level"), bool)
            or not 1 <= payload["level"] <= 5):
        return jsonify({"error": "Informe uma categoria, interesse e intensidade válidos."}), 400
    try:
        with session_scope() as db:
            preference = criar_preferencia(
                db, usuario_id=g.usuario.id, categoria=payload["category"],
                valor=payload["value"], nivel=payload["level"],
            )
            result = {"id": str(preference.id), "category": preference.categoria,
                      "value": preference.valor, "level": preference.nivel}
        return jsonify({"preference": result}), 201
    except IntegrityError:
        return jsonify({"error": "Este interesse já está cadastrado."}), 409
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao criar preferência (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível salvar o interesse agora."}), 503


@api.delete("/api/preferences/<uuid:preference_id>")
@_autenticado_json
def preferences_delete(preference_id: UUID):
    """Remove preferência somente quando ela pertence à sessão atual.

    Parâmetros:
        preference_id: UUID da preferência individual.

    Retorno:
        JSON de confirmação ou HTTP 404 para dados ausentes ou alheios.

    Integração:
        DELETE exige CSRF e o repositório confere proprietário e identificador.
    """
    try:
        with session_scope() as db:
            removed = remover_preferencia(db, usuario_id=g.usuario.id,
                                          preferencia_id=preference_id)
        if not removed:
            return jsonify({"error": "O interesse não foi encontrado nesta conta."}), 404
        return jsonify({"status": "removido"})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao remover preferência (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível remover o interesse agora."}), 503


@api.errorhandler(413)
def too_large(_error):
    """Converte uploads acima do limite configurado em resposta JSON.

    Parâmetros:
        _error: exceção HTTP 413 criada pelo limite de conteúdo do Flask.

    Retorno:
        JSON com mensagem curta e status HTTP 413.

    Integração:
        O cliente JavaScript apresenta o campo ``error`` no estado da interface.

    Tratamento de erros:
        O limite é definido pela fábrica em oito megabytes.
    """
    limit = "3,5 MB" if os.environ.get("VERCEL") == "1" else "8 MB"
    return jsonify({"error": f"Imagem grande demais. O limite é {limit}."}), 413


@api.get("/api/library")
@_autenticado_json
def library_list():
    """Pesquisa, filtra, ordena e pagina a biblioteca pessoal autenticada.

    Retorno:
        JSON com a página de livros, totais da conta, filtros ativos e paginação.

    Integração:
        Parâmetros GET limitados são encaminhados ao repositório SQLAlchemy,
        que aplica o UUID da sessão a todas as consultas.

    Tratamento de erros:
        Entradas inválidas retornam 400; falhas PostgreSQL retornam 503 sem
        revelar detalhes de conexão.
    """
    query = request.args.get("q", "").strip()
    author = request.args.get("author", "").strip()
    subject = request.args.get("subject", "").strip()
    favorite_value = request.args.get("favorites", "false").lower()
    origin_value = request.args.get("origin", "")
    order = request.args.get("sort", "adicionados_recentes")
    if len(query) > 120 or len(author) > 160 or len(subject) > 160:
        return jsonify({"error": "Um dos filtros excede o limite permitido."}), 400
    if favorite_value not in {"true", "false", "1", "0"}:
        return jsonify({"error": "O filtro de favoritos é inválido."}), 400
    if origin_value not in {"", "nacional", "internacional", "nao_informado"}:
        return jsonify({"error": "O filtro de origem da obra é inválido."}), 400
    if order not in {"titulo_asc", "titulo_desc", "autor_asc", "adicionados_recentes", "adicionados_antigos"}:
        return jsonify({"error": "A ordenação solicitada não é permitida."}), 400

    def page_parameter(name: str, default: int, maximum: int) -> int | None:
        """Valida parâmetro de página sem aceitar valores negativos ou excessivos.

        Parâmetros:
            name: nome controlado do parâmetro na query string.
            default: valor adotado quando a query string não o informa.
            maximum: maior valor inteiro permitido para o parâmetro.

        Retorno:
            Inteiro positivo dentro do limite ou `None` quando a entrada é inválida.

        Integração:
            `library_list` usa o resultado para limitar consulta e offset SQL.

        Tratamento de erros:
            Strings não decimais, zero e valores acima do limite são rejeitados.
        """
        raw = request.args.get(name)
        if raw is None:
            return default
        if not raw.isdecimal():
            return None
        value = int(raw)
        return value if 1 <= value <= maximum else None

    page = page_parameter("page", 1, 1_000_000)
    page_size = page_parameter("page_size", 12, 48)
    if page is None or page_size is None:
        return jsonify({"error": "Página ou tamanho inválido; utilize valores positivos dentro do limite."}), 400
    try:
        with session_scope() as db:
            result = listar_pagina_usuario(
                db,
                usuario_id=g.usuario.id,
                consulta=query,
                autor=author,
                assunto=subject,
                favoritos=favorite_value in {"true", "1"},
                origem_obra=origin_value or None,
                ordenacao=order,
                pagina=page,
                tamanho=page_size,
            )
        filtered_total = result["filtered_total"]
        total_pages = (filtered_total + page_size - 1) // page_size
        if page > max(1, total_pages):
            return jsonify({"error": "A página solicitada não existe para os filtros atuais."}), 400
        return jsonify({
            "books": [_serialize_library_item(entry) for entry in result["entries"]],
            "pagination": {"page": page, "page_size": page_size, "total": filtered_total,
                           "total_pages": total_pages},
            "summary": {"total_books": result["total_books"],
                        "total_favorites": result["total_favorites"]},
            "filters": {"q": query, "author": author, "subject": subject,
                        "favorites": favorite_value in {"true", "1"}, "origin": origin_value,
                        "sort": order},
        })
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao consultar biblioteca (%s).", type(error).__name__)
        return jsonify({"error": "A biblioteca está temporariamente indisponível."}), 503


def _serialize_library_item(entry) -> dict[str, Any]:
    """Converte associação e metadados em JSON sem misturar dados pessoais.

    Parâmetros:
        entry: associação carregada com o livro relacionado no PostgreSQL.

    Retorno:
        Dicionário JSON com campos bibliográficos e campos da associação.

    Integração:
        A listagem, detalhes e atualização pessoal usam o mesmo contrato.

    Tratamento de erros:
        Valores complementares malformados são ignorados ou substituídos por
        objetos/listas vazios; campos privados permanecem no escopo da conta.
    """
    book = entry.livro
    metadata = book.metadados if isinstance(book.metadados, dict) else {}
    return {
        "id": str(entry.id),
        "catalog_id": book.identificador_externo,
        "title": book.titulo,
        "author": ", ".join(book.autores or []),
        "authors": book.autores if isinstance(book.autores, list) else [],
        "year": book.ano_publicacao,
        "subjects": book.assuntos if isinstance(book.assuntos, list) else [],
        "genres": book.generos if isinstance(book.generos, list) else [],
        "cover": book.url_capa,
        "subtitle": metadata.get("subtitle"),
        "description": book.descricao or metadata.get("description"),
        "isbn": book.isbn,
        "isbn_10": metadata.get("isbn_10"),
        "isbn_13": metadata.get("isbn_13"),
        "publisher": metadata.get("publisher"),
        "language": metadata.get("language"),
        "page_count": metadata.get("page_count"),
        "metadata_scope": metadata.get("metadata_scope"),
        "metadata_sources": metadata.get("metadata_sources", {}),
        "source": book.origem_catalogo,
        "url": (f"https://openlibrary.org/works/{book.identificador_externo}"
                if book.origem_catalogo == "openlibrary" and book.identificador_externo else None),
        "favorite": bool(entry.favorito),
        "notes": entry.observacoes_pessoais,
        "origin_obra": entry.origem_obra or "nao_informado",
        "added_at": _serialize_timestamp(entry.adicionado_em),
        "updated_at": _serialize_timestamp(entry.atualizado_em),
        "progress": _serialize_progress(
            entry.progresso,
            fallback_total=metadata.get("page_count") if isinstance(metadata.get("page_count"), int) else None,
        ),
    }


def _serialize_timestamp(value: datetime | None) -> str | None:
    """Serializa instantes como ISO 8601 UTC, preservando microssegundos.

    Parâmetros:
        value: timestamp do PostgreSQL, normalmente timezone-aware.

    Retorno:
        Texto ISO 8601 com sufixo `Z` ou `None` quando não há instante.

    Integração:
        A interface interpreta esse instante e o exibe no fuso São Paulo,
        sem alterar o valor persistido no banco.

    Tratamento de erros:
        Valores sem fuso são considerados UTC apenas como compatibilidade com
        dados de driver sem timezone; timestamps do modelo usam TIMESTAMPTZ.
    """
    if value is None:
        return None
    aware_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware_value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@api.get("/api/library/<uuid:item_id>")
@_autenticado_json
def library_detail(item_id: UUID):
    """Retorna detalhes bibliográficos e pessoais do item pertencente à sessão.

    Parâmetros:
        item_id: UUID da associação pessoal da biblioteca.

    Retorno:
        JSON `book` ou HTTP 404 se o item não pertence à conta autenticada.

    Integração:
        A consulta passa pelo repositório, que filtra UUID e proprietário.
    """
    try:
        with session_scope() as db:
            entry = obter_item_usuario(db, usuario_id=g.usuario.id, item_id=item_id)
            if entry is None:
                return jsonify({"error": "O livro não foi encontrado nesta biblioteca."}), 404
            return jsonify({"book": _serialize_library_item(entry)})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao consultar detalhes pessoais (%s).", type(error).__name__)
        return jsonify({"error": "Os detalhes do livro estão temporariamente indisponíveis."}), 503


@api.patch("/api/library/<uuid:item_id>")
@_autenticado_json
def library_update_personal(item_id: UUID):
    """Altera favorito ou observação sem modificar o registro bibliográfico.

    Parâmetros:
        item_id: UUID da associação pertencente à conta autenticada.

    Retorno:
        JSON da associação atualizada, 400 para payload inválido e 404 para
        associação ausente ou pertencente a outra conta.

    Integração:
        PATCH exige CSRF global, valida campos e grava somente na associação.

    Tratamento de erros:
        Indisponibilidade PostgreSQL resulta em 503 sem dados internos.
    """
    payload = request.get_json(silent=True)
    allowed = {"favorite", "notes", "origin_obra"}
    if not isinstance(payload, dict) or not payload or set(payload) - allowed:
        return jsonify({"error": "Informe somente campos pessoais válidos em um objeto JSON."}), 400
    favorite = payload.get("favorite")
    notes = payload.get("notes")
    origin = payload.get("origin_obra")
    if "favorite" in payload and not isinstance(favorite, bool):
        return jsonify({"error": "O favorito deve ser verdadeiro ou falso."}), 400
    if "notes" in payload and (
        notes is not None and (not isinstance(notes, str) or len(notes) > 2000)
    ):
        return jsonify({"error": "A observação deve conter no máximo 2.000 caracteres."}), 400
    if "origin_obra" in payload and origin not in {"nacional", "internacional", "nao_informado"}:
        return jsonify({"error": "A classificação deve ser nacional, internacional ou não informada."}), 400
    try:
        with session_scope() as db:
            entry = atualizar_dados_pessoais(
                db,
                usuario_id=g.usuario.id,
                item_id=item_id,
                favorito=favorite if "favorite" in payload else None,
                observacoes_pessoais=notes,
                atualizar_observacoes="notes" in payload,
                origem_obra=origin if "origin_obra" in payload else None,
            )
            if entry is None:
                return jsonify({"error": "O livro não foi encontrado nesta biblioteca."}), 404
            result = _serialize_library_item(entry)
        return jsonify({"book": result})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao atualizar dados pessoais (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível atualizar os dados pessoais agora."}), 503


@api.post("/api/library")
@_autenticado_json
def library_add():
    """Valida metadados de catálogo e os associa à conta autenticada.

    Retorno:
        JSON com o livro já pertencente à conta; o usuário vem da sessão Flask.

    Tratamento de erros:
        Dados inválidos retornam 400 e indisponibilidade PostgreSQL retorna 503.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Envie os dados de um livro em formato JSON."}), 400
    title = payload.get("title")
    catalog_id = payload.get("catalog_id") or payload.get("id")
    author = payload.get("author", "")
    subjects = payload.get("subjects", [])
    year = payload.get("year")
    cover = payload.get("cover")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict) or len(metadata) > 16:
        return jsonify({"error": "Os metadados complementares são inválidos."}), 400
    allowed_metadata = {"subtitle", "description", "publisher", "language", "page_count", "isbn_10", "isbn_13", "metadata_sources", "edition_id", "edition_source", "metadata_scope"}
    if any(key not in allowed_metadata for key in metadata):
        return jsonify({"error": "Os metadados complementares contêm campos não aceitos."}), 400
    for key, value in metadata.items():
        if key == "metadata_sources":
            provenance_fields = {"subtitle", "description", "publisher", "language", "page_count", "isbn_10", "isbn_13"}
            if not isinstance(value, dict) or any(
                field not in provenance_fields or source not in {"openlibrary", "google_books"}
                for field, source in value.items()
            ):
                return jsonify({"error": "A origem dos metadados é inválida."}), 400
        elif key == "page_count":
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 100000):
                return jsonify({"error": "A quantidade de páginas é inválida."}), 400
        elif key == "edition_source":
            if value not in {None, "google_books"}:
                return jsonify({"error": "A origem da edição é inválida."}), 400
        elif key == "metadata_scope":
            if value not in {"work", "work_and_edition"}:
                return jsonify({"error": "O escopo dos metadados é inválido."}), 400
        elif key in {"isbn_10", "isbn_13"}:
            normalized_isbn = normalize_isbn(value)
            expected_length = 10 if key == "isbn_10" else 13
            if value is not None and (normalized_isbn is None or len(normalized_isbn) != expected_length):
                return jsonify({"error": "O ISBN complementar é inválido."}), 400
        elif key == "edition_id":
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value)):
                return jsonify({"error": "O identificador complementar da edição é inválido."}), 400
        elif value is not None and (not isinstance(value, str) or len(value) > 4000):
            return jsonify({"error": "Um campo bibliográfico complementar é inválido."}), 400
    if metadata.get("metadata_scope") == "work_and_edition" and not (
        metadata.get("edition_id") and metadata.get("edition_source") == "google_books"
    ):
        return jsonify({"error": "A edição complementar não possui identificador consistente."}), 400
    if not isinstance(title, str) or not title.strip() or len(title) > 500:
        return jsonify({"error": "O título do livro é inválido."}), 400
    if not isinstance(catalog_id, str) or not re.fullmatch(r"OL\d+W", catalog_id):
        return jsonify({"error": "O identificador do catálogo é inválido."}), 400
    if not isinstance(author, str) or len(author) > 500:
        return jsonify({"error": "O nome do autor é inválido."}), 400
    if not isinstance(subjects, list) or any(not isinstance(item, str) or len(item) > 160 for item in subjects[:16]):
        return jsonify({"error": "Os assuntos do livro são inválidos."}), 400
    if year is not None and (not isinstance(year, int) or isinstance(year, bool) or not 0 <= year <= 9999):
        return jsonify({"error": "O ano de publicação é inválido."}), 400
    if cover is not None and (
        not isinstance(cover, str)
        or not re.fullmatch(r"https://covers\.openlibrary\.org/b/id/\d+-M\.jpg", cover)
    ):
        return jsonify({"error": "A capa do catálogo é inválida."}), 400
    try:
        with session_scope() as db:
            book = obter_por_catalogo(db, origem="openlibrary", identificador=catalog_id)
            if book is None:
                book = criar_livro(db, titulo=title, autores=[author] if author else [],
                                   identificador_externo=catalog_id, origem_catalogo="openlibrary",
                                   url_capa=cover, ano_publicacao=year, assuntos=subjects[:16],
                                   descricao=metadata.get("description"), metadados=metadata)
            item = adicionar_livro(db, usuario_id=g.usuario.id, livro_id=book.id)
            result = {"id": str(item.id), "title": book.titulo}
        return jsonify(result), 201
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao adicionar livro à biblioteca (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível salvar o livro agora."}), 503
    except ValueError:
        return jsonify({"error": "Os dados bibliográficos enviados são inválidos."}), 400


@api.delete("/api/library/<uuid:item_id>")
@_autenticado_json
def library_remove(item_id: UUID):
    """Remove somente a associação do livro pertencente à conta autenticada.

    Parâmetros:
        item_id: UUID da associação pessoal, nunca um ID de usuário.

    Retorno:
        JSON vazio em sucesso e HTTP 404 para itens de outra conta ou ausentes.
    """
    try:
        with session_scope() as db:
            removed = remover_livro_usuario(db, usuario_id=g.usuario.id, item_id=item_id)
        if not removed:
            return jsonify({"error": "O livro não foi encontrado nesta biblioteca."}), 404
        return jsonify({"status": "removido"})
    except (SQLAlchemyError, RuntimeError) as error:
        LOGGER.error("Falha ao remover associação de livro (%s).", type(error).__name__)
        return jsonify({"error": "Não foi possível remover o livro agora."}), 503
