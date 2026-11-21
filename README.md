# Biblioteca Inteligente

## Apresentação

A Biblioteca Inteligente é um sistema web local desenvolvido como projeto acadêmico de inteligência artificial aplicada às ODS. A proposta aborda tarefas que estudantes e leitores podem enfrentar ao organizar livros, acompanhar leituras e descobrir obras de interesse. O sistema combina reconhecimento de texto em capas, consulta bibliográfica, biblioteca individual, acompanhamento de leitura e recomendações.

O problema descrito é o ponto de partida da proposta; sua abrangência entre o público local ainda precisa ser fundamentada com evidências. O projeto não afirma que a aplicação melhora a alfabetização nem que produz impacto educacional comprovado.

## Integrantes

Os nomes e as contribuições efetivamente realizadas pelos integrantes ainda deverão ser preenchidos pelo grupo antes da entrega acadêmica. Nenhum integrante ou contribuição individual é presumido nesta versão.

## ODS escolhida

**ODS 4 — Educação de Qualidade.** A proposta considera o objetivo de promover educação inclusiva, equitativa e de qualidade e oportunidades de aprendizagem ao longo da vida.

## Meta relacionada

A meta considerada é a **4.6**, relacionada à alfabetização de jovens e adultos e aos conhecimentos básicos de matemática. A relação proposta com o sistema é indireta: a organização de livros e o acompanhamento de atividades de leitura podem apoiar práticas relacionadas à leitura, mas não medem nem comprovam alfabetização. A adequação definitiva desta meta ao problema escolhido ainda depende de validação acadêmica pelo grupo.

## Problema identificado

O projeto aborda dificuldades que estudantes e leitores podem encontrar para organizar bibliotecas pessoais, acompanhar o andamento das leituras e localizar livros relacionados aos próprios interesses. A proposta considera pessoas que buscam iniciar ou manter atividades de leitura, incluindo estudantes de Porto Alegre e de outras regiões do Brasil.

A organização e o acesso a informações bibliográficas podem facilitar algumas tarefas ligadas à leitura. Ainda não foi realizada pesquisa local que determine a prevalência dessas dificuldades ou demonstre uma relação causal com resultados educacionais. A fundamentação e a delimitação do público deverão ser complementadas pelo grupo com fontes e evidências adequadas.

## Justificativa da solução

A Biblioteca Inteligente reúne em uma interface tarefas de identificação, consulta bibliográfica, organização pessoal e acompanhamento de leitura. A proposta procura reduzir a entrada manual de informações e oferecer um local para manter livros, progresso e metas. A utilidade e a efetividade da solução dependem de avaliação; funcionalidades implementadas e testes técnicos não constituem, por si, evidência de impacto educacional.

## Justificativa da inteligência artificial

O RapidOCR aplica modelos de visão computacional para reconhecer texto presente em imagens de capas. Esse recurso pode extrair possíveis títulos e autores sem exigir a digitação de todos os dados. Em um fluxo sem OCR, a pessoa dependeria principalmente de uma busca textual ou do preenchimento manual.

O OCR é o componente baseado em modelos de IA. A ordenação de resultados bibliográficos e as recomendações utilizam critérios heurísticos e metadados disponíveis; essas pontuações não representam probabilidades nem modelos de IA treinados pelo projeto. O catálogo localiza possíveis obras e a pessoa usuária confirma qual delas corresponde à capa.

## Funcionamento do sistema

```text
Imagem da capa
    → validação e preparação no Flask
    → RapidOCR local
    → texto reconhecido
    → busca na Open Library (Google Books opcional)
    → escolha e confirmação pela pessoa usuária
    → biblioteca individual no PostgreSQL
```

As consultas bibliográficas dependem de conectividade externa. A imagem é processada localmente e não é armazenada permanentemente pelo fluxo de reconhecimento.

## Funcionalidades

- Cadastro, login e logout com sessão, proteção CSRF e senha armazenada como hash.
- Reconhecimento de capas por envio de imagem ou captura no navegador.
- Busca manual e por OCR na Open Library; Google Books pode complementar dados quando configurado.
- Confirmação explícita do candidato antes da inclusão na biblioteca.
- Biblioteca individual com pesquisa, filtros, ordenação, paginação, detalhes, favoritos, observações e remoção.
- Progresso de leitura com status, páginas e datas.
- Metas de leitura por período e indicadores de progresso.
- Recomendações heurísticas por assuntos, favoritos e interesses declarados.
- Página pública `/sobre-ods` com a justificativa do projeto, limitações e as quatro perguntas do roteiro acadêmico.

Os dados de contas e da biblioteca atual são persistidos no PostgreSQL local. A chave legada `estante-livros-v1` do `localStorage` não é importada, alterada ou apagada.

## Tecnologias utilizadas

| Tecnologia | Finalidade |
| --- | --- |
| Python 3.12 e Flask | Aplicação web, rotas e integração dos módulos |
| HTML, CSS e JavaScript | Interface, responsividade, eventos e chamadas HTTP |
| RapidOCR e ONNX Runtime | Reconhecimento local de texto em imagens |
| Pillow, NumPy e RapidFuzz | Preparação de imagens e comparação de texto |
| PostgreSQL 17 | Persistência local de contas, livros e dados pessoais |
| SQLAlchemy, Psycopg 3 e Alembic | Acesso ao banco, driver e migrações versionadas |
| Open Library | Catálogo bibliográfico principal |
| Google Books | Fonte complementar opcional, condicionada a chave local |
| unittest e Playwright | Testes automatizados e verificação de interface |

## Arquitetura

O navegador apresenta os templates HTML e aplica os estilos de `static/style.css`. `static/app.js` e `static/auth.js` tratam eventos, enviam formulários e requisições JSON ao Flask e atualizam a interface. `backend/routes.py` valida a sessão, CSRF e entradas; módulos Python especializados processam imagens, consultam catálogos e chamam repositórios. SQLAlchemy e Psycopg acessam o PostgreSQL local, enquanto Alembic mantém o esquema versionado. RapidOCR executa localmente; Open Library e, opcionalmente, Google Books são serviços externos.

## Estrutura do projeto

```text
app.py                         entrada da aplicação Flask
backend/                       rotas, OCR, catálogo, recomendações e repositórios
migrations/                    migrações Alembic
templates/                     páginas HTML, incluindo sobre_ods.html
static/                        CSS e JavaScript do navegador
scripts/                       preparação, execução, verificação e backup local
tests/                         testes Flask, PostgreSQL e fixture OCR
docs/                          arquitetura, justificativa, integração e testes
requirements.txt               dependências Python
INICIAR.bat / PARAR.bat         execução e encerramento no Windows
VERIFICAR.bat                   verificação do ambiente local
```

`.venv/`, `.env`, `postgres/runtime/`, `postgres/data/`, `postgres/logs/`, `postgres/backups/` e os modelos em `models_ocr/` são recursos locais ignorados pelo Git.

## Instalação no Windows

O ambiente de referência utiliza Windows x64 e Python 3.12. Para preparar outro computador:

1. Instalar Python 3.12 x64 e Git.
2. Obter a distribuição binária ZIP do PostgreSQL 17 para Windows x64 pela [página oficial do PostgreSQL para Windows](https://www.postgresql.org/download/windows/), que direciona à distribuição da EDB. Extrair `bin/`, `lib/`, `share/` e licenças em `postgres/runtime/`, preservando essa estrutura.
3. Instalar o código-fonte e abrir a pasta do projeto no PowerShell.
4. Executar a preparação local:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar_ambiente.ps1
```

O script cria ou reutiliza `.venv/`, instala dependências somente no ambiente virtual, copia os modelos OCR para `models_ocr/`, gera `.env` se ainda não existir e inicializa o cluster somente quando o diretório não contém uma instância reconhecida. Dados e configurações existentes são preservados. A primeira instalação requer acesso à internet para dependências; pesquisas bibliográficas também requerem internet.

## Configuração

As configurações locais são mantidas em `.env`, que não deve ser versionado. `.env.example` apresenta os nomes das variáveis sem credenciais. O script de instalação gera chaves locais e protege o arquivo com permissões do Windows. A chave de Google Books é opcional; sem ela, o catálogo principal continua disponível.

Não se deve copiar senhas para este README, para logs ou para o repositório. A instância PostgreSQL do projeto usa `127.0.0.1:5433` e não cria serviço permanente do Windows.

## Inicialização e encerramento

Após a preparação inicial, os arquivos de lote iniciam, encerram e verificam os componentes locais:

- `INICIAR.bat` verifica PostgreSQL, autenticação local e resposta de saúde do Flask antes de abrir o sistema em `http://127.0.0.1:5000`.
- `PARAR.bat` encerra o servidor e solicita parada controlada do cluster pertencente ao projeto.
- `VERIFICAR.bat` distingue componentes instalados, configurados e em funcionamento.

O primeiro provisionamento cria o banco e a conta de aplicação, mas o esquema funcional também precisa receber as migrações Alembic. Com a instância do projeto iniciada, as migrações devem ser aplicadas pelo procedimento administrativo documentado em [docs/MIGRACOES.md](docs/MIGRACOES.md). Não se deve apontar a aplicação ou os testes ao banco principal sem observar as instruções de isolamento.

Para criar um backup local datado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_postgres.ps1
```

Backups permanecem em `postgres/backups/` e não são excluídos automaticamente.

## Como utilizar

1. A pessoa usuária abre a aplicação e cria uma conta.
2. Após o login, a pessoa pode pesquisar um livro ou enviar uma imagem da capa. A captura pela webcam depende da permissão concedida pelo navegador.
3. O OCR apresenta textos e candidatos bibliográficos; a pessoa confere os dados e confirma a obra correta.
4. O livro confirmado aparece na biblioteca individual, onde é possível pesquisar, filtrar, ordenar, consultar detalhes, marcar favorito, registrar observações ou remover a associação.
5. O progresso permite registrar status, páginas e datas. As metas exibem conclusões contabilizadas no período escolhido.
6. As recomendações apresentam obras relacionadas a assuntos e interesses disponíveis, com justificativas heurísticas.

## ODS 4 no site

A página pública [`/sobre-ods`](http://127.0.0.1:5000/sobre-ods) apresenta ODS 4 e meta 4.6, a relação indireta proposta, as limitações e as respostas às quatro perguntas do professor: ODS/meta; problema e público; contribuição da solução; e justificativa da IA em comparação com uma alternativa sem OCR.

## Testes

A verificação local mais recente registrada aprovou **81 testes Python** em `biblioteca_inteligente_test` e **4 testes JavaScript** de datas e rótulos; também passaram `compileall`, `pip check`, `node --check` e Playwright/Edge em 1365×900 e 390×844. A produção Vercel foi publicada e homologada pelo fluxo real descrito em [docs/TESTES.md](docs/TESTES.md): autenticação, catálogo, OCR RapidOCR real, salvamento e persistência no Neon, progresso, metas, recomendações, classificação de origem e apresentação das datas foram exercitados. A validação de viewport móvel hospedado não foi executada nesta rodada.

## Limitações

- A webcam física do notebook ainda depende de homologação manual; testes com câmera virtual não comprovam o funcionamento do dispositivo físico.
- A avaliação reproduzível de OCR contém uma única capa autorizada. O resultado observado não estima a precisão geral.
- A disponibilidade e a qualidade dos metadados dependem dos catálogos externos.
- Google Books está integrado como fonte opcional, mas não foi validado em consulta real com chave configurada.
- Ainda faltam evidências locais sobre o problema, validação acadêmica definitiva do vínculo com a meta 4.6 e confirmação dos nomes e contribuições reais do grupo.
- Não foi medido impacto sobre alfabetização; o sistema não deve ser apresentado como prova de melhoria educacional.

## Apresentação acadêmica

A demonstração pode apresentar primeiro o problema proposto e a relação indireta com a ODS 4; em seguida, mostrar cadastro/login, reconhecimento e confirmação de uma capa, inclusão e consulta da biblioteca, atualização de progresso, criação de uma meta e recomendações. A fala deverá distinguir funcionamento técnico de impacto educacional e registrar as contribuições reais dos integrantes. O roteiro de apoio está em [docs/APRESENTACAO.md](docs/APRESENTACAO.md).

## Referências

- [ONU Brasil — ODS 4: Educação de Qualidade](https://brasil.un.org/pt-br/sdgs/4)
- [Nações Unidas — Goal 4 e meta 4.6](https://sdgs.un.org/goals/goal4)
- [RapidOCR — documentação oficial](https://rapidai.github.io/RapidOCRDocs/main/en/)
- [Flask — documentação](https://flask.palletsprojects.com/)
- [PostgreSQL — documentação](https://www.postgresql.org/docs/)
- [Open Library — Search API](https://openlibrary.org/dev/docs/api/search)
- [IBGE Educa — Alfabetização](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html)

O roteiro original do professor não é distribuído neste repositório. Suas exigências foram revisadas na preparação acadêmica; o documento e sua ausência de redistribuição são registrados localmente.

## Classificação de origem e detalhes

Cada associação pessoal pode ser classificada como Nacional, Internacional ou Não informado, sem inferência por idioma ou editora. O filtro integra pesquisa, autor, assunto, favoritos, ordenação e paginação. Os detalhes mostram datas no formato `DD/MM/AAAA às HH:mm` no fuso `America/Sao_Paulo`; códigos bibliográficos conhecidos recebem rótulos amigáveis. A especificação está em [docs/BIBLIOTECA_ORIGEM_LIVROS.md](docs/BIBLIOTECA_ORIGEM_LIVROS.md).

## Preparação para Vercel e Neon

O modo local continua usando o PostgreSQL portátil e os modelos OCR do projeto. A versão hospedada possui configuração separada em [docs/DEPLOY_VERCEL.md](docs/DEPLOY_VERCEL.md) e [docs/POSTGRESQL_NEON.md](docs/POSTGRESQL_NEON.md), com runtime Python, pool Neon, TLS, cookie seguro e upload compactado no navegador. A versão pública está disponível em [biblioteca-inteligente-sigma.vercel.app](https://biblioteca-inteligente-sigma.vercel.app); a prévia permanece protegida pela autenticação da Vercel.
