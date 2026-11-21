# PostgreSQL Neon

## Configuração

A versão local permanece no PostgreSQL portátil do projeto em `127.0.0.1:5433`. A versão hospedada usa Neon PostgreSQL 17 e exige URLs explícitas com TLS. A configuração seleciona `DATABASE_URL` somente quando o runtime define `VERCEL=1`; na execução Windows, a aplicação continua usando `.env` local.

`DATABASE_URL` deve usar o endpoint pooler e uma role de aplicação com privilégios DML restritos. `DATABASE_URL_ADMIN` deve usar conexão direta e ficar reservada à execução administrativa de Alembic. A aplicação recusa conexão hospedada que aponte a localhost e força `sslmode=require`.

O projeto Neon está configurado na região AWS South America East (São Paulo), com branches `production` e `preview`. As roles de aplicação foram criadas separadamente em cada branch com acesso `read_write` ao banco `biblioteca_inteligente`; a conta administrativa permanece separada. A organização consultada em 21/11/2026 informou o plano `free`. Nenhum upgrade ou serviço pago foi ativado intencionalmente, e nenhuma senha ou URL de conexão é documentada.

## Estado da preparação

O esquema local e o branch Neon `preview` estão na revisão `d1a45f8c2e70`. Depois da homologação dos fluxos de preview, foi criado o snapshot `backup-prod-before-migration-2026-11-21` a partir do branch de produção. A cadeia Alembic foi aplicada ao banco de produção em uma transação, e a revisão `d1a45f8c2e70`, sete tabelas e os privilégios da role de aplicação foram confirmados. A versão Vercel de produção realizou operações reais de leitura e escrita no Neon. Após a homologação, a conta sintética e seus dados foram removidos com autorização; a consulta posterior confirmou ausência da conta e zero associações de biblioteca, progresso e metas. Nenhum dado local foi transferido.

## Migrações

O comando de migração deve apontar a URL administrativa explicitamente, confirmar o projeto e o branch de destino e registrar a revisão final. Migrações não são iniciadas automaticamente ao importar `app.py` ou processar uma rota. Os testes automatizados continuam permitidos somente em `biblioteca_inteligente_test` local; nenhum teste destrutivo deve usar o Neon de produção.

## Recursos e custos

A organização Neon consultada informou o plano `free`. O uso e os limites ainda deverão ser conferidos antes de uso contínuo. Nenhum upgrade ou serviço pago foi solicitado ou ativado intencionalmente.
