"""Pacote dos serviços e das rotas da Biblioteca Inteligente."""

import os
from datetime import timedelta

from flask import Flask, g, jsonify, request, session
from sqlalchemy.exc import SQLAlchemyError

from backend.database import session_scope
from backend.repositories.usuarios import obter_usuario


def create_app() -> Flask:
    """Cria a aplicação Flask e registra suas rotas.

    Retorno:
        Instância Flask configurada para servir o pacote de templates e estáticos.

    Integração:
        O módulo raiz ``app.py`` chama esta fábrica para inicializar o servidor.

    Tratamento de erros:
        Os erros HTTP específicos são tratados pelo blueprint de rotas.
    """
    application = Flask(__name__, template_folder="../templates", static_folder="../static")
    application.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    application.json.ensure_ascii = False
    secret_key = os.environ.get("BIBLIOTECA_SECRET_KEY") or _read_secret_key()
    if len(secret_key) < 32:
        raise RuntimeError("A chave de sessão persistente não está configurada com segurança no .env local.")
    application.config.update(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=True,
    )

    @application.before_request
    def load_authenticated_user():
        """Confirma a conta da sessao antes de qualquer operacao protegida.

        Retorno:
            Nenhum retorno quando a conta permanece valida; remove a sessao
            invalida para que os decoradores respondam conforme o tipo de rota.

        Integracao:
            O identificador assinado pelo Flask e conferido em usuarios via
            repository antes de uma rota privada acessar dados.

        Tratamento de erros:
            Indisponibilidade PostgreSQL resulta em HTTP 503 sem detalhes internos.
        """
        g.usuario = None
        if not session.get("csrf_token"):
            from secrets import token_urlsafe

            session["csrf_token"] = token_urlsafe(32)
        if request.endpoint == "static":
            return None
        user_id = session.get("usuario_id")
        if not user_id:
            return None
        try:
            from uuid import UUID

            with session_scope() as db:
                g.usuario = obter_usuario(db, UUID(str(user_id)))
        except (ValueError, SQLAlchemyError, RuntimeError) as error:
            session.clear()
            if request.endpoint not in {"api.health", "api.login", "api.cadastro", "static"}:
                return jsonify({"error": "O banco de dados esta indisponivel. Tente novamente."}), 503
            application.logger.error("Falha ao validar sessão (%s).", type(error).__name__)
            return None
        if g.usuario is None:
            session.clear()
        return None

    @application.before_request
    def protect_state_changes():
        """Valida token CSRF para requisições que alteram estado.

        Retorno:
            Nenhum valor para tokens válidos; resposta controlada 400 caso
            o cabeçalho ou campo de formulário não corresponda à sessão.

        Integração:
            Templates expõem o token em meta tag e o JavaScript envia
            X-CSRFToken nos POST, PUT, PATCH e DELETE.

        Tratamento de erros:
            Ausência de token ou divergência são rejeitadas antes da rota.
        """
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        from hmac import compare_digest

        submitted = request.headers.get("X-CSRFToken") or request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        valid = bool(submitted and expected and compare_digest(
            submitted.encode("utf-8"), expected.encode("utf-8")
        ))
        if not valid:
            if request.path.startswith("/api/"):
                return jsonify({"error": "A solicitação expirou. Atualize a página e tente novamente."}), 400
            return "A solicitação expirou. Atualize a página e tente novamente.", 400
        return None

    from backend.routes import api

    application.register_blueprint(api)
    return application


def _read_secret_key() -> str:
    """Lê a chave persistente do arquivo local sem exibi-la.

    Retorno:
        Chave configurada ou string vazia quando o campo não existe.

    Integração:
        Usa o mesmo arquivo protegido que contém as credenciais do PostgreSQL.

    Tratamento de erros:
        Arquivo ausente ou ilegível resulta em valor vazio e impede uma chave
        insegura fixa de ser usada pela aplicação.
    """
    from backend.database import ENV_FILE

    try:
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("BIBLIOTECA_SECRET_KEY="):
                return line.partition("=")[2].strip()
    except OSError:
        return ""
    return ""
