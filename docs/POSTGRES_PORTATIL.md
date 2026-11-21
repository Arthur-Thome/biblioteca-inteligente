# PostgreSQL portátil

## Distribuição e proveniência

A [página oficial do PostgreSQL para Windows](https://www.postgresql.org/download/windows/) direciona usuários avançados à distribuição binária ZIP da EDB. O ambiente local validado utiliza PostgreSQL 17.12 x64, com executáveis e bibliotecas em `postgres/runtime/`. Os componentes necessários são extraídos para essa pasta; o projeto não instala serviço permanente, não altera o PATH global e não modifica outra instalação PostgreSQL do computador.

## Estado atual da aplicação

O PostgreSQL não está apenas preparado para uma etapa futura: as rotas atuais utilizam o banco para cadastro/autenticação, biblioteca individual, metadados bibliográficos selecionados, progresso, metas e preferências. SQLAlchemy e Psycopg realizam o acesso por repositórios; Alembic controla o esquema. A aplicação mantém a conta de runtime `biblioteca_app` separada da conta administrativa.

## Configuração e segurança

A instância exclusiva do projeto utiliza `postgres/data/`, logs em `postgres/logs/`, backups em `postgres/backups/`, endereço `127.0.0.1` e porta `5433`. O cluster usa autenticação SCRAM-SHA-256 e aceita conexões apenas pelo loopback. `.env` contém credenciais locais geradas e chave de sessão; deve permanecer ignorado pelo Git e protegido pelas ACLs locais. Os scripts não exibem segredos.

A role `biblioteca_app` não possui privilégios de superusuário, criação de bases ou roles. O runtime tem somente permissões necessárias às tabelas. A conta administrativa é usada no provisionamento e nas migrações. Uma eventual instalação PostgreSQL externa, inclusive serviço em outra porta, permanece independente.

## Inicialização, verificação e parada

`scripts/iniciar_postgres.ps1` verifica a identidade do cluster e a porta antes de iniciar a instância pertencente ao projeto. `scripts/parar_postgres.ps1` solicita parada controlada. `scripts/verificar_ambiente.ps1` verifica os componentes locais, versão, autenticação, privilégios e escuta. Os arquivos `INICIAR.bat`, `PARAR.bat` e `VERIFICAR.bat` integram os procedimentos ao uso diário.

O instalador `scripts/instalar_ambiente.ps1` é idempotente: não executa `initdb` em cluster existente, não substitui credenciais e preserva diretórios com conteúdo não reconhecido. Uma instalação nova precisa receber as migrações conforme [MIGRACOES.md](MIGRACOES.md).

## Migrações

As alterações do esquema são armazenadas em `migrations/versions/`. A revisão final registrada é `c4e8a19f07d2`. A configuração de conexão administrativa é carregada localmente; nenhuma URL ou credencial deve ser colocada no repositório. Os testes e verificações de escrita utilizam exclusivamente `biblioteca_inteligente_test`, sem fallback para a base principal.

## Backup e restauração

O backup usa `pg_dump` em formato customizado e recebe identificador de data/hora:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_postgres.ps1
```

As cópias ficam em `postgres/backups/` e não são removidas automaticamente. A restauração deve ser validada inicialmente em uma base nova e vazia com `pg_restore`, sem `--clean` ou `--create` sobre dados existentes. O procedimento validado e o destino isolado constam no relatório da Etapa 10 em [TESTES.md](TESTES.md); a restauração de teste não alterou a base principal.

## Limites e preservação

O banco local da aplicação contém o esquema PostgreSQL versionado e é a persistência das funcionalidades atuais. Os dados legados em `localStorage` não são importados, alterados ou apagados. A base principal foi verificada sem registros de negócio na revisão final; nenhum dado de usuário foi inventado ou reconstruído. Runtime binário, cluster, logs, backups, `.env` e ambiente virtual permanecem somente no notebook e são ignorados pelo Git.
