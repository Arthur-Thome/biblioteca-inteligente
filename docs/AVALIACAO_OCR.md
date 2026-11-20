# Avaliação do reconhecimento de capas

## Metodologia

O conjunto reutilizável local contém uma imagem real: `tests/fixtures/ocr/hobbit-capa-evidencia.png`, recorte da capa já presente em `docs/evidencias/resultado-ocr-final.png`. O manifesto registra título esperado, autor e origem. Não foram coletadas capas de terceiros.

O script `scripts/avaliar_ocr.py` realiza uma inferência de aquecimento, mede três inferências seguintes e registra a mediana, texto identificado, título/autor recuperáveis, consultas, primeiro candidato e posição correta. A recuperabilidade é calculada por similaridade textual normalizada (RapidFuzz `partial_ratio` >= 80 para título e >= 75 para autor); não é uma métrica de CER/WER. A classificação bibliográfica é confrontada com os candidatos retornados pela Open Library. `--sem-catalogo` executa a porção local sem internet.

O relatório separa o ensaio exploratório de pré-processamento da medição repetível. Variantes foram executadas em três rodadas após carregar o mesmo RapidOCR; a mediana de tempo foi registrada. A execução reproduzível deve ser feita com:

```powershell
.\.venv\Scripts\python.exe scripts\avaliar_ocr.py
```

## Comparação na mesma imagem

| Medida | Fluxo anterior, reconstruído com a mesma saída OCR e API | Fluxo atualizado |
|---|---:|---:|
| Imagens avaliadas | 1 | 1 |
| Título recuperável no OCR | 1/1 (100%) | 1/1 (100%) |
| Autor recuperável no OCR | 1/1 (100%) | 1/1 (100%) |
| Livro correto entre os candidatos aceitos | 0/1 | 1/1 |
| Livro correto em primeiro lugar | 0/1 | 1/1 |
| Mediana de inferência aquecida | não registrada antes da alteração | 1,704 s |

O fluxo anterior foi reexecutado pela lógica antiga de geração de consultas e pontuação, com o mesmo texto OCR e Open Library. As consultas ruidosas não produziram candidatos acima do limiar. No fluxo atualizado, RapidOCR retornou `mTATEEPE`, `HOBBIT`, `THE ENOHIAVTING PERLIDE TO`, `"THE LORD OF THE RINCR` e `JRRTOLKIEN`. O texto esperado foi recuperável; a chamada autenticada `POST /api/recognize` retornou “The Hobbit”, de J.R.R. Tolkien, em primeiro lugar, com pontuação heurística 99,0. O teste visual posterior também exibiu candidatos da própria resposta OCR e completou a confirmação e persistência. Uma execução local posterior sem consulta externa encontrou o mesmo texto e autor recuperáveis, com mediana de 1,984 s; a variação de tempo depende da carga do ambiente.

As taxas acima descrevem apenas esta imagem. Com n=1, elas não estimam a precisão real do sistema nem permitem comparação estatística. A pontuação 99,0 não significa 99% de certeza. A versão anterior não tinha medição de tempo aquecida comparável; os 1,704 s são somente a mediana posterior de três execuções naquele ambiente.

## Experimento de pré-processamento

| Variante | Mediana observada | Texto principal observado |
|---|---:|---|
| RGB com contraste 1,18 (base) | 1,860 s | `HOBBIT`, `THE ENOHIAVTING PERLIDE TO`, `JRRTOLKIEN` |
| Escala de cinza com autocontraste | 2,078 s | `HOBBIT`, com mais fragmentos de ruído |
| Escala de cinza, autocontraste e nitidez | 2,322 s | título de subtítulo mais corrompido |
| Ampliação 2× e contraste | 2,039 s | título principal preservado, mais texto incompleto |

As alternativas não foram ativadas porque pioraram o texto observado e/ou o tempo nessa amostra. A seleção não demonstra que o contraste atual seja ótimo para outras capas.

## Etapa 7 — distinção de autoria em títulos repetidos

Na execução real de 20/11/2026, RapidOCR voltou a recuperar o título e o autor na única capa disponível. A mediana aquecida ficou em 1,847 s, ante a execução de 1,704 s registrada anteriormente; essa variação não representa regressão conclusiva porque há somente uma imagem e a carga local muda entre execuções. Open Library retornou diversas entradas intituladas “The Hobbit”, incluindo autores adicionais. A pontuação foi ajustada para reduzir candidatos sem autor compatível quando o conjunto contém evidência de autoria, e o desempate considera a proporção de tokens do nome reconhecidos. O primeiro candidato observado foi “The Hobbit”, de J.R.R. Tolkien, com 100/100 heurístico; o autor permaneceu no primeiro resultado mesmo quando outras entradas tinham o mesmo título. Esse resultado é somente um caso de avaliação, não uma taxa de precisão generalizável.

## Interpretação e limitações

- A detecção extraiu o título principal e autor, mas apresentou ruído e erros ortográficos no subtítulo e em texto editorial.
- A utilização das caixas mantém a leitura espacial estável e a validação descarta confiança não finita ou fora de 0–1.
- Consultas individuais de linhas mais confiáveis melhoraram a identificação nesta amostra; combinações adjacentes continuam sendo tentadas.
- A correspondência do autor é apenas um reforço limitado de ordenação. O texto do título permanece obrigatório para ultrapassar o limiar.
- A API externa pode variar, falhar ou responder diferente em execuções futuras; a avaliação real depende de internet.
- A ausência de outras capas, especialmente em português, impede afirmar melhoria geral ou apresentar taxa representativa de precisão.
- A webcam física ainda precisa de homologação no notebook. Uma simulação não equivale à validação do dispositivo.

## Reprodução e expansão futura do conjunto

Para adicionar uma imagem autorizada, o conjunto deve registrar no `manifest.json` o caminho, título esperado, autor quando conhecido e origem/permissão. O mesmo conjunto deve ser utilizado antes e depois de qualquer alteração, mantendo a medição do OCR separada da disponibilidade da Open Library.
