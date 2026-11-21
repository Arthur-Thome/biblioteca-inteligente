# Roteiro de apresentação

Este roteiro organiza a demonstração da Biblioteca Inteligente segundo o documento do professor. Os nomes e as contribuições de cada integrante permanecem para confirmação pelo grupo; nenhum papel é atribuído sem registro real.

## 1. Apresentação do projeto

Apresentar a Biblioteca Inteligente como um protótipo web, disponível para execução local e em URL pública, para reconhecer texto em capas, consultar candidatos bibliográficos, organizar uma biblioteca pessoal, acompanhar leituras e obter sugestões por assuntos e interesses. Segundo o responsável, os integrantes participaram coletivamente; apresentar os nomes somente depois da confirmação pelo grupo, sem atribuir tarefas individuais não registradas.

## 2. Problema e público-alvo

Apresentar como problema proposto a dificuldade que estudantes e leitores podem enfrentar para organizar livros, acompanhar leituras e descobrir obras relacionadas a seus interesses. O público considerado inclui pessoas que desejam manter atividades de leitura, incluindo estudantes de Porto Alegre e de outras regiões do Brasil. Explicar que a abrangência local ainda precisa de evidências e validação com o público; a pesquisa nacional de alfabetização não prova esse problema específico.

## 3. ODS 4 e meta 4.6

Apresentar a ODS 4 — Educação de Qualidade e a meta 4.6, que trata de alfabetização de jovens e adultos e conhecimentos básicos de matemática. Explicar os dados nacionais sem misturar metodologias: na pesquisa do Instituto Pró-Livro, 47% foram leitores e 53% não leitores (Brasil, 2024; população de 5 anos ou mais; leitor definido por leitura de livro inteiro ou em partes nos três meses anteriores); no Censo 2022, 11,4 milhões de pessoas com 15 anos ou mais não sabiam ler e escrever um bilhete simples. A relação da aplicação com a meta 4.6 é indireta: a ferramenta apoia organização e descoberta de leituras, sem oferecer ensino de alfabetização ou matemática. Os dados não medem as dificuldades de organização de livros, não são específicos de Porto Alegre e não comprovam melhorias atribuíveis ao sistema.

Referências da fala: [relatório de resultados 2024 do Instituto Pró-Livro](https://www.prolivro.org.br/wp-content/uploads/2024/11/Apresentac%CC%A7a%CC%83o_Retratos_da_Leitura_2024_13-11_SITE.pdf), [definição de alfabetização e resultados do Censo 2022 no IBGE](https://educa.ibge.gov.br/jovens/conheca-o-brasil/populacao/22321-alfabetizacao.html). A pesquisa do Pró-Livro entrevistou 5.504 pessoas com 5 anos ou mais, em 208 municípios; o IBGE considera alfabetizada a pessoa que consegue ler e escrever um bilhete simples no idioma que conhece.

## 4. Justificativa da solução

Explicar que a confirmação bibliográfica, o cadastro pessoal, os filtros, o acompanhamento de páginas, as metas e as recomendações reduzem tarefas de organização e oferecem uma forma de acompanhar livros. Descrever essas funcionalidades como contribuição esperada, cuja efetividade depende de avaliação com participantes.

## 5. Justificativa da inteligência artificial

Explicar que o RapidOCR aplica visão computacional para reconhecer texto de uma imagem de capa e reduzir digitação manual. O catálogo usa o texto extraído para pesquisar candidatos. A pontuação não representa probabilidade, e a pessoa usuária confirma o livro correto antes de salvar.

## 6. Tecnologias

Apresentar Python 3.12, Flask, HTML, CSS, JavaScript, RapidOCR, Pillow/NumPy, Open Library, PostgreSQL 17 local, SQLAlchemy, Alembic e Psycopg. Google Books permanece opcional e depende de configuração local. O OCR usa modelos locais; as buscas de catálogo dependem de internet.

## 7. Demonstração ao vivo

### Preparação

1. Confirmar que o notebook está ligado à energia e que a pasta do projeto contém `.venv`, `.env` e os modelos OCR locais.
2. Executar `INICIAR.bat` e aguardar a confirmação de saúde do Flask e abertura do navegador.
3. Entrar com uma conta de demonstração preparada pelo grupo ou cadastrar uma conta temporária antes da apresentação. A senha deve permanecer privada e não deve aparecer em slides, terminal projetado ou repositório.
4. Para busca bibliográfica, confirmar conexão com a internet. Sem rede, o OCR local continua disponível, mas a consulta Open Library pode falhar e a interface deverá informar indisponibilidade.
5. Selecionar uma capa conhecida disponibilizada legitimamente para a demonstração. A homologação da webcam física deve ser feita no próprio notebook; a câmera virtual não substitui esse teste.

### Fluxo demonstrativo

1. Mostrar a biblioteca pessoal e os controles de pesquisa, filtro, ordenação e detalhes.
2. Enviar uma capa de teste ou capturá-la pela webcam física, se homologada.
3. Mostrar o texto do OCR e explicar que a inferência ocorre localmente com RapidOCR.
4. Mostrar os candidatos bibliográficos da Open Library e confirmar manualmente a obra correta.
5. Salvar o livro e atualizar a página para demonstrar persistência no PostgreSQL.
6. Abrir os detalhes e atualizar status, páginas lidas e datas; mostrar o percentual somente quando houver total conhecido.
7. Criar uma meta, apresentar o período e explicar que o progresso deriva de livros concluídos no intervalo.
8. Gerar recomendações e explicar os assuntos/interesses relacionados. Reforçar que não há probabilidade de acerto nem garantia de recomendação.
9. Abrir `/sobre-ods` sem conta Vercel e apresentar os dois indicadores com seus recortes, as quatro perguntas, a relação proposta com a meta 4.6 e as limitações. O login interno continua necessário para páginas e dados pessoais da biblioteca.
10. Encerrar a sessão e executar `PARAR.bat` para desligar o Flask e solicitar parada segura do PostgreSQL do projeto.

### Plano alternativo

Se a webcam física estiver indisponível ou negada pelo navegador, usar o envio de arquivo e informar a limitação. Se a Open Library estiver indisponível, mostrar a mensagem real de erro e explicar que o serviço é externo; não substituir a resposta por dados fictícios. Se o OCR não reconhecer a capa, usar busca manual ou outra imagem autorizada e apresentar a falha como limitação do reconhecimento.

## 8. Resultados de testes

O registro mais recente informa 78 testes automatizados aprovados, incluindo rotas, repositórios PostgreSQL, autenticação, CSRF, isolamento, OCR, catálogo, progresso, metas, recomendações e página ODS. O fluxo Playwright da Etapa 9 percorreu funcionalidades na base isolada e resoluções de notebook e celular. A equipe deverá apresentar números apenas conforme a execução mais recente documentada em `docs/TESTES.md`.

Os testes técnicos não medem aprendizagem nem comprovam impacto sobre alfabetização. A amostra de avaliação OCR é pequena e não sustenta taxa geral de precisão.

## 9. Limitações

- A relação com a meta 4.6 é indireta e ainda precisa de validação acadêmica.
- A dificuldade local de organização de leituras ainda não foi medida com participantes.
- A webcam física ainda depende de homologação no notebook de apresentação.
- OCR pode falhar em capas inclinadas, estilizadas, pequenas, desfocadas ou com baixo contraste.
- Catálogo e recomendações dependem de dados e disponibilidade externa da Open Library.
- A amostra OCR disponível é pequena; não deve ser apresentada como benchmark representativo.
- A contribuição educacional não foi medida.
- A participação individual dos integrantes deve corresponder ao trabalho efetivamente realizado.

## 10. Conclusão

Concluir que o sistema demonstra uma aplicação local de visão computacional para apoiar identificação e organização de livros. Reafirmar que a confirmação permanece com a pessoa usuária e que a relação educacional é uma proposta sujeita à avaliação. Não alegar melhoria comprovada de alfabetização.

## Orientações ao grupo

O grupo deverá revisar o fluxo, testar as falas e preencher a tabela abaixo com contribuições confirmadas por cada integrante. A preparação não atribui atividades fictícias.

| Integrante confirmado pelo grupo | Contribuição efetivamente realizada | Parte da apresentação assumida |
|---|---|---|
| A preencher | A preencher com registro confirmado | A definir pelo grupo |
| A preencher | A preencher com registro confirmado | A definir pelo grupo |
| A preencher | A preencher com registro confirmado | A definir pelo grupo |
| A preencher | A preencher com registro confirmado | A definir pelo grupo |
| A preencher | A preencher com registro confirmado | A definir pelo grupo |

Os registros não utilizados deverão ser removidos pelo grupo para adequar a tabela ao número real de integrantes. O professor limita a equipe a cinco integrantes; a composição real ainda não foi confirmada na documentação.
