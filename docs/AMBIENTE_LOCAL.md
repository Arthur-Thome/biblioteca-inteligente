# Ambiente local no Windows

## Componentes

O ambiente de referência utiliza Windows x64, Python 3.12 em `.venv/` e PostgreSQL 17 portátil em `postgres/runtime/`. O cluster de dados permanece em `postgres/data/`, os registros em `postgres/logs/` e os backups em `postgres/backups/`. Os modelos RapidOCR ficam em `models_ocr/` para permitir inferência local após a instalação inicial.

A aplicação Flask utiliza PostgreSQL para contas, catálogo selecionado, associações de biblioteca, progresso, metas e preferências. O acesso ocorre por SQLAlchemy/Psycopg e pelas rotas e repositórios de `backend/`. As migrações versionadas ficam em `migrations/`; a versão aplicada consta em `alembic_version`.

## Preparação inicial

Antes de executar o instalador, a distribuição PostgreSQL 17 x64 deve estar extraída em `postgres/runtime/`, com `bin/initdb.exe`, `lib/` e `share/`. O procedimento cria ou reutiliza `.venv/`, instala `requirements.txt` nesse ambiente, copia os modelos RapidOCR locais, gera `.env` com valores aleatórios quando não houver configuração e provisiona a instância exclusiva do projeto. O script evita inicializar dados já existentes que não possuam os marcadores do projeto.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar_ambiente.ps1
```

O instalador prepara o banco e a conta de aplicação, mas não aplica automaticamente o esquema de negócio. Para uma instalação nova, iniciar a instância e seguir [MIGRACOES.md](MIGRACOES.md), aplicando Alembic à base configurada antes de usar as rotas que dependem das tabelas.

## Operação

- `INICIAR.bat` verifica o PostgreSQL e inicia o Flask após confirmar a resposta HTTP de saúde.
- `PARAR.bat` encerra os processos do projeto de forma controlada.
- `VERIFICAR.bat` verifica dependências, arquivos, modelos, autenticação e disponibilidade.
- `scripts/backup_postgres.ps1` cria um dump com data e hora, sem excluir cópias anteriores.

Os scripts usam caminhos relativos à raiz, não alteram o PATH nem a política global do PowerShell e não criam serviço Windows permanente. O banco escuta em `127.0.0.1:5433`; o Flask usa `127.0.0.1:5000`.

## Configuração e proteção

`.env` contém credenciais locais e a chave de sessão, é protegido por ACL durante a preparação e está ignorado pelo Git. `.env.example` contém somente campos vazios. O runtime Flask usa a conta `biblioteca_app`, sem privilégios administrativos; migrações são executadas com a conta administrativa local. Nenhuma senha deve ser copiada para documentação, argumentos de shell ou logs.

O cluster usa SCRAM-SHA-256 e aceita conexões somente no loopback. Dados, runtime, logs e backups ficam no notebook e não são publicados. Os modelos OCR também permanecem fora do Git; sua disponibilidade local evita novos downloads para inferência após a preparação.

## Dependências externas

A primeira preparação requer acesso ao índice de pacotes Python. Pesquisas bibliográficas e recomendações consultam a Open Library e, portanto, podem depender de internet. Google Books é complementar e requer uma chave local para consultas ao provedor. O processamento OCR utiliza modelos locais.

## Verificações registradas

Na revisão final documentada em [TESTES.md](TESTES.md), PostgreSQL local autenticou as contas do projeto, a aplicação Flask respondeu e os modelos OCR foram executados sem acesso externo. A restauração foi ensaiada em uma base nova e isolada. A webcam física não foi homologada; a versão com câmera virtual não substitui esse teste.

## Diagnóstico

Quando a inicialização falha, executar `VERIFICAR.bat` e consultar mensagens sem expor `.env`. Se a porta 5433 estiver ocupada, identificar o processo antes de alterar configuração; nenhum processo de outra instalação deve ser encerrado pelos scripts. Se a rota de saúde não responder, conferir `logs/flask-error.log` e o estado do PostgreSQL do projeto. A instalação não recria clusters, não remove dados e não importa dados legados de `localStorage`.
