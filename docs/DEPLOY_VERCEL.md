# Implantação na Vercel

## Arquitetura

`app.py` exporta a fábrica Flask para o runtime Python 3.12 da Vercel. O hook de build em `pyproject.toml` copia `static/` para `public/static/`, diretório distribuído pela CDN. A execução Windows continua servindo os arquivos originais de `static/` e não depende do Neon.

`vercel.json` inclui os templates, módulos backend, migrações e modelos OCR no pacote da função. A dependência `VERCEL=1` seleciona explicitamente a configuração hospedada: a aplicação exige `DATABASE_URL`, TLS e chave de sessão persistente, utiliza cookies `Secure` e limita o corpo HTTP a 3.500.000 bytes. O navegador reduz imagens grandes para JPEG até 3.300.000 bytes apenas na versão hospedada; a instância local mantém o limite de 8 MiB.

## Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `DATABASE_URL` | URL do Neon com pooler e role de aplicação com DML restrito |
| `BIBLIOTECA_SECRET_KEY` | Chave aleatória persistente para assinar sessões HTTPS |
| `DATABASE_URL_ADMIN` | URL direta de administração usada somente por migrações controladas |
| `POSTGRES_APP_USER` | Nome da role de runtime referenciada pela migração de privilégios |
| `POSTGRES_ADMIN_USER` | Nome da role proprietária referenciada pela migração de privilégios |
| `GOOGLE_BOOKS_API_KEY` | Chave opcional; Open Library continua disponível sem ela |

As URLs do banco e a chave de sessão devem ser cadastradas como variáveis sensíveis da Vercel. A configuração não contém fallback para `127.0.0.1`. A role de runtime não deve receber privilégios administrativos. A URL administrativa não deve ser exposta ao navegador nem ser necessária durante uma requisição comum.

## Migrações e publicação

As migrações Alembic são executadas em uma etapa administrativa controlada, nunca em cada requisição. A revisão de origem individual é `d1a45f8c2e70`. A implantação de pré-visualização deve usar o branch de teste do Neon; a produção deve receber seu esquema somente depois da validação da pré-visualização.

As alterações devem ser publicadas primeiro na branch de trabalho. Após o build, a homologação deve conferir cadastro, login, sessão, CSRF, consultas PostgreSQL, OCR real, upload, catálogo, filtros, progresso, metas, recomendações e os viewports desktop/celular. Uma implantação pronta não comprova esses fluxos por si só.

## Estado da implantação

A revisão local passou em 81 testes Python e quatro testes JavaScript. A validação visual local passou em 1365×900 e 390×844. O branch Neon `preview` está no esquema `d1a45f8c2e70` e a role de aplicação foi verificada por consulta autenticada. O projeto Vercel `biblioteca-inteligente` foi vinculado ao repositório `Arthur-Thome/biblioteca-inteligente`, com instalação do GitHub App limitada a esse repositório. A Vercel criou um deployment inicial READY a partir de `main`, mas ele ainda não foi homologado e não corresponde à branch de implementação. As variáveis sensíveis de Preview estão configuradas somente para `feat/hosting-neon-detales-origem`, usando a branch Neon de teste. O primeiro deployment de pré-visualização da branch atual ainda precisa ser gerado e validado. O Neon de produção permanece sem migrações e sem variáveis de produção.

## Limitações da plataforma

O limite de upload fica abaixo do teto padrão de requisições da função. RapidOCR e ONNX Runtime são empacotados com modelos locais, sem envio da imagem a um serviço OCR externo. A primeira inicialização do modelo pode elevar a latência; bundle, memória e inferência precisam ser medidos na pré-visualização. Nenhum plano pago deve ser ativado automaticamente.

## Referências técnicas

- [Flask na Vercel](https://vercel.com/docs/frameworks/backend/flask)
- [Runtime Python](https://vercel.com/docs/functions/runtimes/python)
- [Limitações das funções](https://vercel.com/docs/functions/limitations)
- [Documentação Neon](https://neon.com/docs)
