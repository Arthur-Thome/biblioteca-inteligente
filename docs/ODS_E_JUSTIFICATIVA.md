# ODS 4 e justificativa do projeto

## Problema proposto e público

A proposta considera as dificuldades que estudantes e leitores podem encontrar para organizar suas bibliotecas pessoais, acompanhar leituras e descobrir livros relacionados a seus interesses. O público hipotético inclui pessoas estudantes e leitoras de Porto Alegre e de outras regiões do Brasil. A abrangência e a frequência dessas dificuldades ainda precisam ser verificadas com evidências locais e participação do público; o projeto não conduziu pesquisa com usuários para estabelecer prevalência.

O Censo Demográfico 2022 do IBGE oferece contexto nacional sobre alfabetização: 11,4 milhões de pessoas com 15 anos ou mais declararam não saber ler e escrever um bilhete simples, e os resultados apontam diferenças entre grupos populacionais. Esses dados demonstram que alfabetização permanece uma questão educacional relevante no país; não demonstram que a dificuldade de organizar leituras seja causa do analfabetismo, nem que o sistema proposto altere os indicadores.

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
- IBGE Educa. [Alfabetização — resultados do Censo Demográfico 2022](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html). Consulta realizada em 20 de novembro de 2026.
- IBGE. [Censo Demográfico 2022: Alfabetização — Resultados do universo](https://biblioteca.ibge.gov.br/visualizacao/periodicos/3108/cd_2022_alfabetizacao.pdf).

## Pendências acadêmicas

Ainda não há coleta local de dados sobre a organização de bibliotecas ou continuidade de leitura, avaliação com participantes, comprovação de impacto, validação definitiva do vínculo com a meta 4.6 nem registro das contribuições efetivamente realizadas por cada integrante. Essas limitações permanecem explícitas na página `/sobre-ods`.
