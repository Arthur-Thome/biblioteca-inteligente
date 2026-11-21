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

A revisão local passou em 81 testes Python e quatro testes JavaScript. A validação visual local passou em 1365×900 e 390×844. O branch Neon `preview` está no esquema `d1a45f8c2e70` e a role de aplicação foi verificada por consulta autenticada. O projeto Vercel `biblioteca-inteligente` está vinculado ao repositório `Arthur-Thome/biblioteca-inteligente`, com o GitHub App limitado a esse repositório. O deployment de Preview do commit `63d4b6c` está READY e utiliza somente o branch Neon de teste. A prévia continua protegida pela autenticação da Vercel. O branch de produção foi migrado até `d1a45f8c2e70` após a criação do snapshot `backup-prod-before-migration-2026-11-21`; as cinco variáveis de produção foram cadastradas sem expor seus valores. O banco de produção continua sem contas, livros ou dados de homologação.

## Limitações da plataforma

O limite de upload fica abaixo do teto padrão de requisições da função. RapidOCR e ONNX Runtime são empacotados com modelos locais, sem envio da imagem a um serviço OCR externo. A primeira inicialização do modelo pode elevar a latência; bundle, memória e inferência precisam ser medidos na pré-visualização. Nenhum plano pago deve ser ativado automaticamente.

## Homologação da prévia em 21/11/2026

O GitHub OAuth e o GitHub App da Vercel foram vinculados ao repositório `Arthur-Thome/biblioteca-inteligente`, com acesso restrito a esse repositório. O deployment de prévia do commit `bee37e8` ficou READY. A página inicial, `/sobre-ods`, `static/style.css`, `static/app.js` e `static/formatters.js` responderam HTTP 200. Pelo Opera, uma conta ficcional exclusiva foi criada e autenticada na branch Neon `preview`, `The Hobbit` foi pesquisado na Open Library, adicionado à biblioteca e permaneceu após recarregar. O modal apresentou as datas no padrão `DD/MM/AAAA às HH:mm`, no fuso de São Paulo.

A homologação identificou dois ajustes: o catálogo retornou o código `cat`, sem rótulo legível, e um texto auxiliar descrevia incorretamente a base como PostgreSQL local. O mapa foi ampliado para Catalão e os textos passaram a descrever o PostgreSQL associado ao ambiente em execução. O deployment mais recente confirmou a correção do rótulo no modal. A classificação individual Nacional foi salva e exibida no card.

Na implantação `dpl_4zxGAe3qw7HebaahR3PGwMrct1u3`, o upload de `tests/fixtures/ocr/hobbit-capa-evidencia.png` executou o RapidOCR real no runtime Linux. O OCR retornou texto reconhecível, incluindo fragmentos de “The Hobbit” e “J.R.R. Tolkien”; a consulta real à Open Library apresentou seis candidatos, com “The Hobbit” e J.R.R. Tolkien em primeiro lugar. A aplicação não salvou outro registro automaticamente. O fluxo confirmou upload, inferência hospedada e retorno de candidatos, mas não caracteriza uma avaliação ampla de precisão nem mede a latência de ponta a ponta.

Essa prévia permanece protegida pela autenticação da Vercel e utiliza somente o branch Neon `preview`. No Opera, o progresso de leitura foi salvo como “Lendo” com 45/310 páginas (15%); uma meta de um livro foi criada e persistiu; recomendações reais retornaram nove sugestões derivadas dos assuntos do livro. O endpoint `/api/recommend` respondeu HTTP 200. Login, persistência, busca bibliográfica, OCR real, formatação de datas, idioma traduzido, classificação individual, progresso, metas e recomendações foram verificados na prévia. Naquele registro da prévia, viewport mobile hospedado, limpeza da conta sintética e validação da produção ainda estavam pendentes; a produção e a limpeza são descritas abaixo.

## Referências técnicas

- [Flask na Vercel](https://vercel.com/docs/frameworks/backend/flask)
- [Runtime Python](https://vercel.com/docs/functions/runtimes/python)
- [Limitações das funções](https://vercel.com/docs/functions/limitations)
- [Documentação Neon](https://neon.com/docs)
## Homologação de produção — 21/11/2026

A produção foi publicada e acessada pela URL pública `https://bibliotecainteligente.vercel.app`. A página inicial, `/sobre-ods`, `/api/health` e recursos estáticos foram verificados. O fluxo real no Opera confirmou autenticação, consulta à Open Library, upload e inferência RapidOCR em Linux com uma capa de evidência, seleção de candidato, persistência no Neon após recarga, detalhes, classificação da obra, progresso, metas e recomendações. Uma consulta de logs registrou HTTP 200 para `/api/recognize`.

A conta e os registros sintéticos da homologação foram excluídos após autorização. A consulta de verificação confirmou que os registros associados foram removidos. O teste não incluiu inspeção de viewport móvel diretamente hospedado; os viewports mobile e notebook estão cobertos somente pela execução local descrita em `docs/TESTES.md`. A webcam física não foi homologada.

O estado READY da implantação e o fluxo funcional foram observados; esses resultados não constituem medição de disponibilidade contínua. A conta/plano de cobrança não foi verificada de forma conclusiva nesta rodada. Não foi ativado intencionalmente nenhum serviço pago.

Em seguida, `bibliotecainteligente.vercel.app` foi adicionado ao mesmo projeto como domínio verificado; as respostas públicas de `/`, `/sobre-ods` e `/api/health` foram confirmadas. A tentativa de adicionar `biblioteca-inteligente.vercel.app` retornou HTTP 409 `owned-on-other-team`, pois o nome já pertence a outro projeto. O Codex não tentou transferir nem modificar o domínio atribuído a terceiros. O domínio curto alternativo é agora o endereço de compartilhamento recomendado.
