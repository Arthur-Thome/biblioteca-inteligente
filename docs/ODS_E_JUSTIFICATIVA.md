# ODS 4 e justificativa do projeto

## Problema proposto e público

A proposta considera as dificuldades que estudantes e leitores podem encontrar para organizar suas bibliotecas pessoais, acompanhar leituras e descobrir livros relacionados a seus interesses. O público hipotético inclui pessoas estudantes e leitoras de Porto Alegre e de outras regiões do Brasil. A abrangência e a frequência dessas dificuldades ainda precisam ser verificadas com evidências locais e participação do público; o projeto não conduziu pesquisa com usuários para estabelecer prevalência.

As fontes nacionais contextualizam a importância social da leitura e da alfabetização, mas não medem o problema específico de organização de bibliotecas:

- A 6ª edição da pesquisa *Retratos da Leitura no Brasil*, do Instituto Pró-Livro, foi coletada entre 30 de abril e 31 de julho de 2024, com entrevistas domiciliares presenciais a 5.504 pessoas alfabetizadas ou não, com 5 anos ou mais, em 208 municípios. O resultado permite leitura nacional. A pesquisa classificou como leitor quem leu, inteiro ou em partes, ao menos um livro de qualquer gênero, impresso ou digital, nos três meses anteriores. Nessa edição, 47% foram leitores e 53% não leitores. Não leitor declarou não ter lido livro nem parte de livro nos três meses, mesmo que tenha lido nos últimos 12 meses.
- O Censo Demográfico 2022 do IBGE registrou 11,4 milhões de pessoas com 15 anos ou mais que não sabiam ler e escrever um bilhete simples: 7,0% de 163 milhões nessa faixa etária. O indicador deriva do questionário do Universo, aplicado em todos os municípios brasileiros; para o IBGE, a alfabetização considera ler e escrever pelo menos um bilhete simples no idioma que a pessoa conhece.

Os indicadores se referem a pesquisas, amostras/populações e métodos diferentes; não devem ser somados nem apresentados como uma única medição. Eles descrevem o contexto do Brasil, não Porto Alegre especificamente. Não demonstram que dificuldade de organizar leituras cause analfabetismo, nem que o sistema proposto altere qualquer indicador.

## ODS e meta relacionadas

A ODS 4 busca assegurar educação inclusiva, equitativa e de qualidade e promover oportunidades de aprendizagem ao longo da vida. A meta 4.6 trata de garantir que jovens e uma proporção substancial de adultos alcancem alfabetização e conhecimentos básicos de matemática. A seleção da meta é uma relação proposta e indireta: a ferramenta apoia organização, descoberta e acompanhamento de atividades de leitura, mas não oferece alfabetização, ensino de matemática ou avaliação de aprendizagem.

Por isso, a conexão deverá permanecer descrita como contribuição potencial de apoio à leitura. A implementação técnica e os testes de software não constituem evidência de impacto educacional. Uma validação acadêmica definitiva precisa delimitar o público, coletar evidências sobre a necessidade específica, justificar a escolha da meta e definir uma avaliação compatível com o escopo e com a ética de pesquisa da disciplina.

## Solução implementada e contribuição esperada

A aplicação identifica texto em capas usando RapidOCR local, consulta candidatos bibliográficos e exige confirmação humana. Também permite formar uma biblioteca por conta, acompanhar estado e páginas lidas, definir metas e receber recomendações por assuntos e interesses registrados. A contribuição esperada consiste em reduzir etapas de entrada manual e organizar informações relacionadas à leitura. A efetividade dessa contribuição ainda depende de avaliação com participantes; ela não é apresentada como resultado comprovado.

## Justificativa da inteligência artificial

O modelo pré-treinado de visão computacional RapidOCR extrai possíveis títulos e autores diretamente de imagens de capas. Sem OCR, a interação dependeria mais da digitação manual ou da busca textual. O catálogo externo localiza candidatos a partir do texto extraído, mas não constitui a IA e não confirma sozinho a identidade da obra. A pessoa usuária revisa e confirma o livro antes de salvá-lo. O sistema não treina um modelo de alfabetização, não mede leitura e não interpreta o OCR como certeza.

## Correspondência com o roteiro do professor

O documento `docs/referencias/Roteiro do documento final..pdf` possui três páginas; a primeira funciona como capa e as páginas seguintes apresentam o enunciado. O roteiro pede um problema real associado a uma das 17 ODS, identificação da meta, explicação do público e importância, justificativa da solução e da IA, sistema funcional com interface e operação ponta a ponta, código em repositório com README e apresentação ao vivo. O ponto de partida da aplicação pública preserva as quatro perguntas e a orientação de que a tecnologia deve decorrer do problema. O roteiro também pede participação de todos no desenvolvimento e na apresentação; nomes e contribuições reais ainda devem ser registrados pelo grupo, sem atribuições inventadas.

## Referências

- Nações Unidas Brasil. [ODS 4 — Educação de Qualidade](https://brasil.un.org/pt-br/sdgs/4). Consulta realizada em 20 de novembro de 2026.
- United Nations Department of Economic and Social Affairs. [Goal 4: Quality Education — targets and indicators](https://sdgs.un.org/goals/goal4). Consulta realizada em 20 de novembro de 2026.
- Instituto Pró-Livro. [6ª edição da pesquisa Retratos da Leitura no Brasil — apresentação de resultados 2024 (PDF)](https://www.prolivro.org.br/wp-content/uploads/2024/11/Apresentac%CC%A7a%CC%83o_Retratos_da_Leitura_2024_13-11_SITE.pdf). Metodologia, definição de leitor e resultados nacionais.
- Instituto Pró-Livro. [Edições da pesquisa Retratos da Leitura no Brasil](https://www.prolivro.org.br/pesquisas-retratos-da-leitura/as-pesquisas-2/).
- Instituto Pró-Livro. [Pesquisa aponta que mais da metade dos brasileiros não lê livros](https://www.prolivro.org.br/2024/12/04/pesquisa-aponta-que-mais-da-metade-dos-brasileiros-nao-le-livros/). Publicado em 4 de dezembro de 2024.
- IBGE Educa. [Alfabetização — resultados do Censo Demográfico 2022](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html). Consulta realizada em 20 de novembro de 2026.
- IBGE. [Censo Demográfico 2022: Alfabetização — Resultados do universo](https://biblioteca.ibge.gov.br/visualizacao/periodicos/3108/cd_2022_alfabetizacao.pdf).

## Pendências acadêmicas

Ainda não há coleta local de dados sobre a organização de bibliotecas ou continuidade de leitura, avaliação com participantes, comprovação de impacto, validação definitiva do vínculo com a meta 4.6 nem registro das contribuições efetivamente realizadas por cada integrante. Essas limitações permanecem explícitas na página `/sobre-ods`.
