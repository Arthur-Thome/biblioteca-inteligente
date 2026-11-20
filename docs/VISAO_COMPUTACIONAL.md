# Visão computacional e reconhecimento de capas

## Fluxo implementado

1. A interface autenticada aceita uma imagem JPG, PNG ou WEBP, com limite HTTP de 8 MB.
2. `POST /api/recognize` exige sessão válida e CSRF. O backend lê os bytes e verifica formato, decodificação e limite de 40 milhões de pixels antes de inicializar o OCR.
3. `backend.visao_computacional.extract_cover_text` corrige orientação EXIF, converte para RGB e reduz proporcionalmente imagens a no máximo 1700 × 1700. O contraste recebe o ajuste moderado 1,18 que já existia.
4. `get_ocr_engine` carrega uma única instância RapidOCR de forma tardia, com modelos locais de `models_ocr/`. Um lock protege inferências concorrentes.
5. O RapidOCR fornece caixas de texto, texto e confiança por linha. As detecções com confiança finita entre 0,30 e 1,00 são ordenadas de cima para baixo e da esquerda para a direita quando as caixas são válidas; coordenadas ausentes ou inválidas preservam a ordem fornecida.
6. `suggest_search_queries` prioriza linhas com maior confiança e combina janelas próximas. A confiança serve somente para ordenar consultas; ela não é probabilidade de título correto.
7. A rota envia no máximo três consultas à Open Library, deduplica obras e ordena candidatos por pontuação heurística. Só apresenta candidatos com pontuação igual ou superior a 50.
8. O navegador apresenta texto e candidatos. A confirmação explícita da pessoa usuária continua necessária para gravar a associação à biblioteca no PostgreSQL.

## Modelos e bibliotecas

O motor verificado é RapidOCR 3.10.0, com ONNX Runtime e modelos presentes na pasta ignorada `models_ocr/`. Pillow 12.3.0 prepara as imagens; NumPy produz o bitmap; RapidFuzz 3.14.6 calcula similaridade. Nenhuma imagem é enviada à Open Library: somente termos de consulta bibliográfica são enviados pela conexão HTTPS.

A documentação oficial do RapidOCR descreve `boxes` como coordenadas de quatro pontos por linha, `txts` como o texto associado, `scores` como confiança por linha e `elapse` como duração de inferência ([documentação de uso](https://rapidai.github.io/RapidOCRDocs/main/en/install_usage/rapidocr/usage/)). A implementação utiliza caixas, texto e confiança; a duração é medida pelo script local de avaliação.

## Preparação, limites e falhas

- A orientação EXIF é corrigida antes da conversão. A imagem não é gravada em disco pelo endpoint.
- O limite de upload do Flask é 8 MB e o backend limita a imagem decodificada a 40 milhões de pixels. Uma miniatura proporcional restringe o bitmap enviado ao modelo.
- Não há correção automática de perspectiva ou rotações alternativas. Em ensaio exploratório com a única capa local disponível, escala de cinza com autocontraste, nitidez e ampliação não melhoraram o texto e aumentaram o tempo; por isso, não foram adicionadas ao caminho padrão.
- OCR sem texto retorna listas vazias e orientação para busca manual. Falha de inicialização/inferência retorna erro controlado. Falhas de catálogo preservam o texto detectado e orientam a busca manual.
- O processamento local não possui cancelamento rígido de inferência por tempo. O lock serializa chamadas ao motor; um lote com várias imagens não é permitido pela rota.

## Consultas e classificação

As consultas usam linhas OCR e janelas adjacentes ordenadas pela confiança média, com um bônus pequeno apenas para evitar que toda combinação fique atrás de uma linha isolada. A classificação calcula RapidFuzz `token_set_ratio` (75%) e `partial_ratio` (25%). Títulos formados por palavras funcionais isoladas recebem redução para conter falsos positivos. Quando pelo menos um candidato apresenta evidência textual de autor, uma proporção maior de tokens do nome reconhecidos aumenta a pontuação em até 12 pontos; autoria divergente recebe penalidade heurística de 18 pontos. Empates priorizam maior proporção de autor reconhecido. Sem evidência de autor, títulos não recebem essa penalidade. O limiar 50 e os ajustes são regras operacionais heurísticas, não probabilidades calibradas.

Os campos bibliográficos continuam sendo tratados como dados externos não confiáveis. Candidatos de baixa pontuação não aparecem como identificações confirmadas. O navegador permite editar a busca manual, escolher candidato ou cancelar sem adicionar livro automaticamente.

## Limitações

O conjunto local contém somente uma capa real reutilizável, “The Hobbit”, recortada da captura existente em `docs/evidencias/resultado-ocr-final.png`. Assim, os resultados não sustentam generalização para capas portuguesas, letras estilizadas, inclinação, baixa iluminação, outros idiomas ou classes de fundo. O banco PostgreSQL continua responsável pela biblioteca após confirmação; a visão computacional não altera contas, tabelas ou dados existentes.

## Homologação manual da webcam física

O inventário de dispositivos do Windows foi bloqueado por permissão de acesso CIM nesta execução; a disponibilidade da webcam física não pôde ser determinada, e a webcam não foi testada nem aprovada. A homologação deverá ocorrer no notebook de apresentação:

1. Executar `INICIAR.bat` e abrir a aplicação em `http://127.0.0.1:5000`.
2. Entrar com uma conta autorizada de teste e selecionar **Usar câmera**.
3. Aceitar a permissão de câmera do navegador quando solicitada. Se houver recusa, conferir as permissões do site nas configurações do navegador sem desativar proteções do Windows.
4. Posicionar uma capa real, imóvel e legível no quadro e pressionar **Fotografar agora**.
5. Confirmar que a prévia aparece e que o indicador da câmera se encerra após a captura.
6. Pressionar **Analisar capa** e conferir texto, candidatos e mensagem de estado. Confirmar manualmente um resultado somente se título e autoria estiverem corretos.
7. Registrar navegador, dispositivo, título testado, resultado e aprovação/falha em evidência acadêmica sem incluir credenciais.
