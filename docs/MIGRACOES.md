# Migrações versionadas

## Ferramenta e configuração

O projeto usa Alembic com SQLAlchemy 2 e driver Psycopg 3. `alembic.ini` aponta para `migrations/`; `migrations/env.py` importa metadados de `backend.models` e lê credenciais locais sem gravá-las na configuração versionada. A conexão de migração usa a role administrativa. O runtime da aplicação usa a role restrita `biblioteca_app`.

## Revisões entregues

- `b86bc6695616`: cria usuários, livros, bibliotecas pessoais, progresso, metas e preferências, com chaves, índices e restrições.
- `766b3c6df106`: adiciona verificações do ISBN canônico e do formato de arrays JSONB.
- `887b2bb10d3d`: concede DML à role runtime e registra privilégios padrão sem permitir CREATE no schema.
- `9a7d31f2c4e8`: acrescenta a coluna JSONB `livros.metadados`, com `{}` como padrão; preserva linhas e campos anteriores.
- `c4e8a19f07d2`: acrescenta favorito e observações pessoais à associação `biblioteca_usuario`, com padrão compatível, limite de 2.000 caracteres, índice por proprietário e sem alterar dados bibliográficos compartilhados.

As revisões não copiam `localStorage` e não são executadas na inicialização Flask. Alembic registra o estado em `alembic_version`.

## Comandos locais

```powershell
\.venv\Scripts\python.exe -m alembic current
\.venv\Scripts\python.exe -m alembic history
\.venv\Scripts\python.exe -m alembic check
\.venv\Scripts\python.exe -m alembic upgrade head
```

O destino padrão é `biblioteca_inteligente`. Para operar a base isolada de integração, configura-se somente o nome permitido na sessão PowerShell:

```powershell
$env:BIBLIOTECA_DATABASE_NAME = 'biblioteca_inteligente_test'
\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:BIBLIOTECA_DATABASE_NAME
```

O módulo de conexão aceita apenas o banco principal ou o nome exato terminado em `_test`; o script de preparação verifica a propriedade e nunca recria nem limpa a base existente.

## Processo seguro

Antes de uma migração no banco principal, deve existir dump recente validado com `pg_restore --list`. As revisões são primeiro aplicadas e testadas em `biblioteca_inteligente_test`; depois a revisão e o alvo são conferidos e o upgrade explícito é executado no principal. Os testes de integração não limpam nem usam o banco principal. A criação de tabelas ocorre apenas por Alembic, nunca em `create_all()` no start da aplicação.

As migrações devem ser revisadas junto com os modelos e testadas contra PostgreSQL real. `alembic check` compara metadados compatíveis com autogeração; restrições CHECK podem exigir revisão manual, pois o comparador de Alembic não identifica todas as diferenças desse tipo. As revisões incluem operações explícitas e versionadas.

Downgrade pode remover tabelas ou dados. Nenhum downgrade deve ser aplicado ao banco principal sem backup, análise da revisão e autorização específica. O procedimento de recuperação prioriza restaurar o dump em banco separado e validar antes de qualquer troca de configuração.
