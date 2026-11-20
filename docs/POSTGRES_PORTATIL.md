# PostgreSQL portátil

## Distribuição e proveniência

A [página oficial do PostgreSQL para Windows](https://www.postgresql.org/download/windows/) direciona usuários avançados à distribuição binária ZIP da EDB. Foi utilizada a versão PostgreSQL 17.12 para Windows x64, listada na [página oficial de binários da EDB](https://www.enterprisedb.com/download-postgresql-binaries). A página consultada não disponibilizava checksum oficial para o ZIP. O arquivo teve a integridade estrutural ZIP verificada e seu SHA-256 local foi registrado em `docs/TESTES.md`; esse valor não é apresentado como checksum oficial.

Foram extraídos `bin/`, `lib/`, `share/` e arquivos de licença para `postgres/runtime/`. Não foram instalados serviços Windows, não foi alterado o PATH global e não foi instalado componente externo do sistema. As bibliotecas de runtime Visual C++ necessárias já estavam disponíveis no Windows examinado.

## Configuração e segurança

A instância usa `postgres/data/`, logs em `postgres/logs/`, endereço `127.0.0.1` e porta `5433`. O cluster foi inicializado com autenticação SCRAM-SHA-256 para conexões locais e TCP. A configuração limita o listener ao loopback; não há acesso pela rede externa. O serviço PostgreSQL 18 preexistente na porta 5432 foi mantido sem alteração.

O arquivo `.env` contém credenciais aleatórias locais para administração e para a aplicação. O script de preparação restringe sua ACL às contas locais identificadas no ambiente e não escreve os valores nos logs. O arquivo é ignorado pelo Git. `biblioteca_app` não possui SUPERUSER, CREATEDB, CREATEROLE ou CREATE no schema. A role administrativa é proprietária dos bancos e aplica migrações; a conta de runtime possui conexão, uso do schema e permissões DML nas tabelas.

A dependência Psycopg 3 foi declarada em `requirements.txt` e instalada exclusivamente em `.venv/` para conexões futuras. O driver não é utilizado pela aplicação Flask nesta etapa.

## Operação

`scripts/iniciar_postgres.ps1` verifica o marcador do cluster e a porta antes de iniciar somente o PostgreSQL do projeto. `scripts/parar_postgres.ps1` solicita parada `smart`, sem encerramento forçado. `scripts/verificar_ambiente.ps1` testa autenticação administrativa e da aplicação, versão, privilégios e endereço de escuta. Os scripts são repetíveis e não executam `initdb` sobre um cluster existente.

O backup é criado em formato customizado e recebe data/hora no nome:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_postgres.ps1
```

Backups ficam em `postgres/backups/`, ignorados pelo Git, e não são removidos automaticamente. Um dump gerado foi lido com `pg_restore --list`. A restauração não foi executada durante esta etapa.

## Restauração futura

Antes de restaurar, deve ser preservado um backup atualizado do banco de destino. Para evitar substituição de dados, a validação inicial deve criar um banco novo e vazio, conferir que o PostgreSQL do projeto está iniciado e restaurar o dump nele com `pg_restore --no-owner --dbname biblioteca_inteligente_teste caminho\do\arquivo.dump`, usando credencial administrativa por mecanismo seguro como `PGPASSFILE` temporário com ACL restrita. O banco existente não deve receber opções de limpeza (`--clean` ou `--create`) sem procedimento de migração e autorização específica. Após a restauração, devem ser conferidos o conteúdo esperado e os logs; credenciais não devem ser colocadas na linha de comando ou no histórico do shell.

## Limites desta etapa

As rotas Flask não consultam PostgreSQL. As migrações criaram as tabelas iniciais de contas, livros, bibliotecas, progresso, metas e preferências, mas não existem registros reais de negócio. A biblioteca permanece no `localStorage` existente; não foi lida, removida ou migrada. A integração dos repositórios com Flask e a autenticação pertencem a etapas posteriores.
