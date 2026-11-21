# PostgreSQL Neon

## Configuração

A versão local permanece no PostgreSQL portátil do projeto em `127.0.0.1:5433`. A versão hospedada usa Neon PostgreSQL 17 e exige URLs explícitas com TLS. A configuração seleciona `DATABASE_URL` somente quando o runtime define `VERCEL=1`; na execução Windows, a aplicação continua usando `.env` local.

`DATABASE_URL` deve usar o endpoint pooler e uma role de aplicação com privilégios DML restritos. `DATABASE_URL_ADMIN` deve usar conexão direta e ficar reservada à execução administrativa de Alembic. A aplicação recusa conexão hospedada que aponte a localhost e força `sslmode=require`.

O projeto Neon foi criado no plano gratuito, na região AWS South America East (São Paulo), com um branch `production` e um branch isolado `preview`. As roles de aplicação foram criadas separadamente em cada branch com acesso `read_write` ao banco `biblioteca_inteligente`. A conta administrativa permanece separada. Nenhuma senha ou URL de conexão é documentada.

## Estado da preparação

O esquema local foi atualizado para a revisão `d1a45f8c2e70` depois de backup. O branch Neon de pré-visualização precisa receber e validar a cadeia Alembic antes da produção. O branch de produção permanece sem migração de negócio até a homologação da pré-visualização. A criação do projeto e dos branches não transfere contas nem livros do PostgreSQL local.

## Migrações

O comando de migração deve apontar a URL administrativa explicitamente, confirmar o projeto e o branch de destino e registrar a revisão final. Migrações não são iniciadas automaticamente ao importar `app.py` ou processar uma rota. Os testes automatizados continuam permitidos somente em `biblioteca_inteligente_test` local; nenhum teste destrutivo deve usar o Neon de produção.

## Recursos e custos

A configuração inicial utiliza o plano gratuito existente e computação mínima. Nenhum upgrade ou serviço pago foi solicitado ou ativado. O uso e os limites devem ser conferidos antes da divulgação para usuários reais.
