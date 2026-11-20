# Diagnóstico inicial

## Escopo e evidências

O diagnóstico foi realizado por leitura dos arquivos da raiz, `templates/`, `static/` e `tests/`. O ambiente virtual `.venv/` existe, mas seu conteúdo foi excluído da análise detalhada por ser dependência instalada, não fonte do projeto. A aplicação e os testes não foram executados nesta etapa.

O arquivo `Roteiro do documento final..pdf` não foi encontrado na raiz nem nos arquivos visíveis do projeto. Portanto, as exigências do professor consideradas aqui são somente as fornecidas no enunciado desta etapa. A raiz não contém `.git`; assim, o diretório aberto ainda não se apresenta como repositório Git. Não foram encontrados `AGENTS.md` nem documentos em `docs/` antes deste diagnóstico.

## Estado e estrutura encontrados

```text
AGENTS.md                         regras permanentes registradas nesta etapa
README.md                         documentação atual do protótipo
INICIAR_WINDOWS.bat               cria ambiente virtual, instala requisitos e inicia Flask
requirements.txt                  dependências Python declaradas
app.py                            aplicação Flask, OCR, catálogo e recomendações
templates/index.html              interface única servida por Flask
static/style.css                  estilos da interface
static/app.js                     câmera, busca, biblioteca local e recomendações
tests/test_app.py                 testes unittest com mocks
docs/DIAGNOSTICO_INICIAL.md       este diagnóstico
docs/MAPA_ATUAL_DO_CODIGO.md      fluxos atuais verificados
docs/PLANO_DE_MIGRACAO.md         proposta para etapas futuras
.venv/                            ambiente virtual local já existente
```

Não foram encontrados outros diretórios-fonte relevantes na raiz. Não há estrutura de migrações, configuração de banco, arquivos SQL, configuração de empacotamento, `.env.example` ou Git ignore visível na raiz. O fato de não serem visíveis não comprova ausência fora da pasta examinada.

## Funcionalidades implementadas

- Flask serve a página `/`, fornece `/api/health`, `/api/search`, `/api/recognize` e `/api/recommend`, e trata upload acima do limite com resposta 413.
- `app.py` inicia o servidor Flask somente em `127.0.0.1:5000`, com `debug=False`.
- O upload é limitado a 8 MB no Flask. A rota verifica arquivo vazio e validade básica por abertura/verificação com Pillow; a interface também restringe extensão MIME declarada e tamanho.
- `extract_cover_text` corrige orientação EXIF, converte e reduz a imagem, ajusta contraste e usa RapidOCR. As caixas/textos com confiança mínima de 0,30 são filtradas e o resultado é limitado a 30 itens.
- O backend combina linhas candidatas, pesquisa até três expressões na Open Library, calcula similaridade por RapidFuzz e ordena candidatos. A confirmação para adicionar é feita pela pessoa usuária no navegador.
- A busca manual usa a Open Library. A recomendação agrega assuntos associados aos livros enviados pelo navegador e exclui os identificadores já salvos.
- O navegador mantém a biblioteca em `localStorage`, adiciona e remove livros localmente e apresenta contagem, estados vazios, resultados OCR/busca e recomendações.
- O JavaScript oferece captura por câmera via `getUserMedia`, além de envio de arquivo.
- A suíte contém nove testes `unittest` que usam Flask test client e mocks para rotas, normalização, livro inválido, OCR simulado, busca e recomendações. Ela não mede qualidade real de OCR.

## Funcionalidades incompletas frente ao projeto previsto

- Não há cadastro, login, sessão ou separação de dados por conta.
- Não há PostgreSQL, modelos persistentes, migrações nem camada de acesso a dados.
- Biblioteca, inclusões e remoções existem apenas no `localStorage` de um navegador; progresso de leitura, metas e preferências não são implementados.
- O catálogo integrado é Open Library; Google Books não aparece no código.
- Não há demonstração local/offline de catálogo nem garantia de que os modelos OCR estarão pré-baixados.
- Não há scripts separados para verificar configuração, iniciar/parar serviços com segurança ou fazer backup. O BAT instala pacotes em cada execução e mantém o servidor aberto até interrupção manual.
- Não há documentação acadêmica que evidencie avaliação da ODS/meta ou participação real dos integrantes. Essas informações dependem do grupo e não podem ser inventadas.

## Dependências e execução

`requirements.txt` declara Flask `>=3,<4`, Pillow `>=10,<13`, Requests `>=2.31,<3`, RapidFuzz `>=3.5,<4`, NumPy `>=1.26,<3`, RapidOCR `>=3,<4` e ONNX Runtime `>=1.18,<2`. Não há arquivo de lock nem versão exata de Python fixada pelos metadados; o README recomenda Python 3.11 ou 3.12 de 64 bits, embora o contexto do projeto estabeleça 3.12. A compatibilidade efetiva de todas as combinações, especialmente wheels de NumPy/ONNX Runtime/RapidOCR para a instalação Python local, não foi verificada.

`INICIAR_WINDOWS.bat` prefere `py -3`, cria `.venv` quando ausente, executa `pip install -r requirements.txt` e chama `app.py`. Isso exige internet na instalação inicial, conforme README, e não abre navegador automaticamente. O reconhecimento inicial pode buscar modelos OCR; catálogo e capas dependem de serviços externos. Não foram executados o BAT, instalação, importação do ambiente virtual ou verificações de versões, em conformidade com as restrições da etapa.

## Visão computacional

RapidOCR com backend ONNX Runtime realiza OCR local. O backend carrega o mecanismo sob demanda e usa locks para inicialização/inferência; Pillow processa a imagem e NumPy fornece a matriz RGB. O OCR extrai texto, não detecta semanticamente capas nem identifica o livro sozinho. A identificação é uma busca heurística em catálogo externo seguida de escolha humana.

A lógica de transformação, geração de consulta e pontuação está em funções Python (`extract_cover_text`, `suggest_search_queries`, `score_ocr_match`) e pode ser testada em partes. Os testes atuais simulam OCR; um teste de integração com OCR real depende de dependências, modelos locais e imagem de referência, e não foi executado. Limitações visíveis incluem limiar heurístico fixo, seleção simples das primeiras/maiores linhas, dependência de cobertura e assuntos da Open Library, e ausência de validação de acurácia com conjunto de capas rotuladas.

## Frontend e integração

Há uma página HTML, um CSS e um JavaScript. O HTML referencia ambos por `url_for('static', ...)`. O CSS define layouts, componentes, cores, estados e breakpoints em 800 px e 480 px, mas está concentrado em regras extensas/minificadas e não possui comentários didáticos. O HTML não possui comentários explicativos por seção; o JavaScript não documenta individualmente suas funções. Essa situação diverge das regras permanentes registradas em `AGENTS.md` para alterações e documentação futuras.

Os detalhes dos controles, classes, IDs, eventos e rotas constam em `MAPA_ATUAL_DO_CODIGO.md`. A interface atual tem fluxos funcionais representados no código, porém não implementa as telas de autenticação e progresso exigidas para a visão final.

## Persistência e integridade

O backend não grava a biblioteca. O navegador envia os livros atuais no corpo JSON de `/api/recommend`; o servidor filtra alguns campos e consulta o catálogo. Portanto, os dados existentes a preservar são os itens que possam estar armazenados no `localStorage` do navegador usado para demonstração, além dos próprios arquivos-fonte. O conteúdo do navegador não foi acessado nem copiado nesta análise. Antes da migração futura, deve-se orientar exportação/backup local desses dados, com consentimento, sem os inserir no Git.

A migração para PostgreSQL deverá introduzir contas e chaves estrangeiras, biblioteca por usuário, progresso, metas e preferências, restrições de integridade, migrações e cópias de segurança locais. A aplicação não deve criar banco ou substituir dados sem plano de backup e validação.

## Segurança e riscos observados

- Não foram reportados valores de segredos. Não há arquivo de configuração `.env` visível na raiz, nem credenciais de banco no código examinado.
- A ausência de autenticação é expressa no README e confirmada pelas rotas; o endpoint de recomendações aceita payload de qualquer cliente. Isso é aceitável apenas como protótipo local sem contas, mas não atende ao isolamento necessário para múltiplos usuários.
- O limite de requisição é 8 MB e há validação por Pillow, reduzindo riscos de upload. Ainda não há armazenamento de upload, allowlist baseada em formato decodificado explícita nem validação de dimensões/consumo de processamento além dos limites e proteções da biblioteca.
- `/api/recommend` recebe objetos controlados pelo cliente. `valid_books` limita quantidade e valida identificador, mas assume que `subjects` é uma lista fatiável; estruturas inesperadas podem gerar erro não tratado. Convém normalizar tipos e limites de comprimento em todas as propriedades.
- Erros de OCR são registrados com `LOGGER.exception`; a mensagem apresentada ao cliente é genérica. Falhas de catálogo incluem texto de exceção no log, o que deve continuar sem incluir conteúdo sensível.
- O backend envia consultas derivadas do texto OCR à Open Library; o README já documenta esse fluxo. A imagem não é gravada pelo código examinado.
- As capas são buscadas diretamente de `covers.openlibrary.org`; logo, a interface requer rede para imagens remotas e transmite IP/metadados de requisição ao host externo.
- O BAT instala dependências automaticamente sem arquivo de lock. Não foi encontrado `.gitignore` na raiz; deve-se criar um antes de versionamento para excluir `.venv`, segredos, caches, modelos, bancos e backups. A falta de Git impede verificar o que seria incluído em um commit.
- A aplicação liga apenas em loopback e desativa modo debug, o que combina com apresentação local. Não deve ser exposta à rede sem revisão de autenticação, autorização e controles adicionais.

## Compatibilidade acadêmica e ODS

O protótipo demonstra uma interface e integração real de OCR com pesquisa de catálogo e recomendação por assuntos, mas não constitui por si só evidência de melhoria de alfabetização. A proposta deve descrever com precisão o benefício como apoio à organização e descoberta de leituras, relacionando-o à ODS 4/meta 4.6 como hipótese de contribuição indireta, sem afirmar impacto comprovado. O grupo deve conferir o texto oficial da meta e definir indicadores e método de avaliação antes de alegar resultados.

README, tecnologias e instruções de execução existem em forma inicial. Repositório GitHub, publicação de código, documentação acadêmica final e apresentação ao vivo ainda não foram comprovados. O PDF do professor está ausente; requisitos adicionais desse roteiro permanecem pendentes. A participação de integrantes deve ser registrada somente após confirmação das contribuições e do plano de apresentação pelo grupo.

## Verificações realizadas

- Leitura estática dos arquivos de aplicação, interface, dependências, inicializador e testes.
- Verificação de presença dos caminhos autorizados e do PDF solicitado.
- Não foram executados testes automatizados, servidor, instalação, scripts de inicialização ou operações de banco. Essas verificações permanecem pendentes.
