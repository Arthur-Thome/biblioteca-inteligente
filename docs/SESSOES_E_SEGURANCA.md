# Sessões e segurança

## Cookie e chave local

A `SECRET_KEY` é gerada criptograficamente pelo instalador local e fica no `.env` protegido, ignorado pelo Git. A aplicação recusa iniciar se a chave não estiver configurada com comprimento mínimo de 32 caracteres. O cookie é `HttpOnly`, `SameSite=Lax` e, para a apresentação por HTTP em `127.0.0.1`, `Secure=False`. A validade é de oito horas e a renovação ocorre durante o uso. A sessão assinada contém apenas o UUID da conta e token CSRF; a senha e o hash não entram no cookie.

Uma implantação futura com HTTPS deverá definir `SESSION_COOKIE_SECURE=True` e tratar o segredo por um mecanismo de configuração protegido apropriado. A configuração local da apresentação não deve ser reutilizada como configuração pública.

## CSRF e rotas privadas

O Flask cria token aleatório associado à sessão em páginas HTML e verifica `X-CSRFToken` ou `csrf_token` de formulário em POST, PUT, PATCH e DELETE. Login, cadastro, logout e APIs de alteração usam a mesma proteção. Token ausente ou inválido recebe resposta controlada HTTP 400. O navegador obtém o token de uma meta tag e o script envia o cabeçalho nas mutações.

Antes de uma rota protegida, o UUID do cookie é convertido e consultado na tabela `usuarios`; uma conta inexistente invalida o estado. Páginas privadas redirecionam ao login e APIs respondem 401. O endpoint operacional `/api/health` permanece público e não apresenta estado sensível.

## Senhas e tentativas

Werkzeug calcula hashes scrypt com salt. A comparação ocorre no servidor; respostas não diferenciam usuário desconhecido e senha incorreta. O limitador por origem e usuário aplica uma pausa temporária após oito falhas dentro de dez minutos. O estado existe na memória do processo, não bloqueia permanentemente contas e não exige serviço externo.

## Limites do ambiente

O banco aceita conexão apenas no loopback local e a aplicação utiliza a conta PostgreSQL de runtime. Logs registram a classe do erro de banco sem incluir texto da exceção ou credenciais. Candidatos da Open Library são atribuídos ao DOM por `textContent`; imagens de capa aceitam somente o domínio e o padrão HTTPS previstos. A senha não é armazenada no navegador. As requisições de OCR e busca externa continuam dependendo de conexão com Open Library.
