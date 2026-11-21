# Banco de dados PostgreSQL

## Metadados complementares (Etapa 7)

A tabela `livros` possui `metadados` JSONB com objeto vazio padrão, adicionado pela revisão `9a7d31f2c4e8`. O campo preserva valores editoriais opcionais que não possuem coluna própria e a origem informada para cada campo. Colunas e índices anteriores permanecem intactos; nenhum ISBN de obra agregada é gravado sem vínculo de edição confirmado.

## Estado

O banco local `biblioteca_inteligente` recebeu as migrações versionadas da Etapa 4. Na Etapa 5, o cadastro grava contas e a API Flask lê e grava novas associações da biblioteca por conta utilizando os repositórios existentes. A chave `estante-livros-v1` não é consultada, alterada nem importada. Os testes de autenticação e propriedade utilizam somente `biblioteca_inteligente_test`.

O destino de integração utiliza PostgreSQL 17.12 em `127.0.0.1:5433`, Psycopg 3 e SQLAlchemy. A migração usa Alembic e autenticação local protegida pelo `.env`.

## Modelo relacional

Na Etapa 9, o banco não recebeu nova migração: as tabelas `progresso_leitura`, `metas_leitura` e `preferencias` já existentes foram integradas às rotas autenticadas. O banco principal permaneceu sem usuários, livros e associações. O inventário da Etapa 9 registrou dois usuários, dois livros e uma associação em `_test`, sem origem identificada. Na verificação final da Etapa 10, a base `_test` apareceu sem registros de domínio; a causa da diferença não foi determinada e nenhum backup separado dessa base estava disponível para comparação. As operações seguem usando a conta de runtime com privilégio restrito.

Na Etapa 8, `biblioteca_usuario` também armazena `favorito` (booleano, padrão falso), `observacoes_pessoais` (texto opcional limitado a 2.000 caracteres) e o timestamp de atualização já existente. A revisão `c4e8a19f07d2` adiciona a restrição CHECK e índice composto por proprietário/favorito. Os campos pessoais permanecem separados de `livros`.

```mermaid
erDiagram
    USUARIOS ||--o{ BIBLIOTECA_USUARIO : possui
    LIVROS ||--o{ BIBLIOTECA_USUARIO : referencia
    BIBLIOTECA_USUARIO ||--o| PROGRESSO_LEITURA : registra
    USUARIOS ||--o{ METAS_LEITURA : define
    USUARIOS ||--o{ PREFERENCIAS : seleciona

    USUARIOS {
        uuid id PK
        varchar nome
        varchar nome_usuario UK
        varchar senha_hash
        timestamptz criado_em
        timestamptz atualizado_em
    }
    LIVROS {
        uuid id PK
        varchar titulo
        jsonb autores
        text descricao
        varchar isbn UK
        varchar identificador_externo
        varchar origem_catalogo
        text url_capa
        integer ano_publicacao
        jsonb generos
        jsonb assuntos
        jsonb metadados
        timestamptz criado_em
        timestamptz atualizado_em
    }
    BIBLIOTECA_USUARIO {
        uuid id PK
        uuid usuario_id FK
        uuid livro_id FK
        timestamptz adicionado_em
    }
    PROGRESSO_LEITURA {
        uuid id PK
        uuid biblioteca_usuario_id FK_UK
        varchar status
        integer paginas_lidas
        integer total_paginas
        timestamptz iniciado_em
        timestamptz concluido_em
        text observacoes
    }
    METAS_LEITURA {
        uuid id PK
        uuid usuario_id FK
        integer quantidade_objetivo
        date periodo_inicio
        date periodo_fim
    }
    PREFERENCIAS {
        uuid id PK
        uuid usuario_id FK
        varchar categoria
        varchar valor
        varchar valor_normalizado
        integer nivel
    }
```

## Tabelas e integridade

- `usuarios`: nome de exibição, identificador normalizado e hash Werkzeug da senha. O identificador é único e as rotas conferem o hash antes de criar uma sessão.
- `livros`: o registro mantém o escopo de obra ou edição em `metadados.metadata_scope`; candidatos Open Library podem começar em nível de obra. Autores, gêneros, assuntos e metadados complementares são JSONB. O ISBN canônico é opcional; ISBN normalizado e par origem/identificador externo possuem unicidade parcial. O título não é único, pois títulos iguais podem corresponder a edições distintas.
- `biblioteca_usuario`: relação N:N entre usuários e livros, única por par usuário/livro. Consultas, leitura e exclusão recebem o identificador do proprietário.
- `progresso_leitura`: no máximo um registro por associação. A coluna `status` é a fonte única de estado, com `nao_iniciado`, `lendo`, `concluido` ou `abandonado`. Restrições rejeitam contagens negativas, total inválido, progresso maior que o total e datas inconsistentes.
- `metas_leitura`: objetivo positivo por período, único por usuário e intervalo exato. O progresso da meta deverá ser derivado dos registros de leitura; não é armazenado como contador duplicado.
- `preferencias`: gênero ou assunto, intensidade de 1 a 5 e valor normalizado único por usuário/categoria.

Todas as entidades usam UUID. Datas de evento usam `TIMESTAMPTZ`, armazenado pelo PostgreSQL com conversão de fuso; períodos de metas usam `DATE`. `criado_em` e `atualizado_em` estão presentes nas entidades temporais principais.

As chaves estrangeiras usam `RESTRICT`. A exclusão da associação remove explicitamente seu progresso e preserva o registro bibliográfico compartilhado. Uma conta com dados relacionados não é apagada por cascata. Índices cobrem nome de usuário, catálogos/ISBN, coleção por dono e período, e preferências.

## Acesso e responsabilidades

As credenciais da role `postgres` são usadas somente por Alembic e rotinas de administração. A role `biblioteca_app` não é superusuária, não cria bancos, roles ou objetos de esquema; possui conexão, uso de schema e DML nas tabelas. As migrações criam as tabelas como administradora e aplicam privilégios padrão DML à conta de runtime.

O módulo [database.py](../backend/database.py) carrega `.env` sem imprimir credenciais, restringe o destino ao banco principal ou ao sufixo isolado `_test`, cria engine Psycopg e fornece sessões com commit/rollback e fechamento. As rotas de autenticação, biblioteca, progresso, metas e preferências usam `usuarios`, `livros`, `biblioteca_usuario`, `progresso_leitura`, `metas_leitura` e `preferencias`; a identidade vem do UUID guardado na sessão Flask e validado em cada requisição. Os endpoints privados filtram pelo proprietário e as mutações exigem CSRF.

## Backup e recuperação

O [script local de backup](../scripts/backup_postgres.ps1) cria dumps customizados datados em `postgres/backups/`, sem sobrescrever arquivos anteriores. A restauração da Etapa 10 foi validada em `biblioteca_inteligente_restore_20261120`, banco novo e isolado, sem executar `--clean` no banco principal. Os resultados estão registrados em `docs/TESTES.md`.

## Limites

O banco principal local avançou da revisão `c4e8a19f07d2` para `d1a45f8c2e70` após backup customizado datado em `postgres/backups/`; a alteração adiciona apenas `origem_obra`, seu CHECK e índice. A base de teste também recebeu a migração Alembic. Nenhum livro, conta ou dado pessoal foi importado do navegador.

O Neon foi preparado com PostgreSQL 17, branch de produção e branch isolado de pré-visualização no plano gratuito. Os dados do PostgreSQL local não foram copiados. O esquema de produção online só deve ser migrado depois da homologação do branch de pré-visualização. As URLs pooler de aplicação e direta administrativa são separadas, usam TLS e não são registradas neste documento. Consulte `docs/POSTGRESQL_NEON.md` para o estado operacional e a execução controlada de migrações.
