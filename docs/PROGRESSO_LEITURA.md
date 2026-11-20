# Progresso de leitura

## Persistência e estados

O progresso pertence à linha `progresso_leitura`, ligada à associação individual `biblioteca_usuario`. Os estados válidos são `nao_iniciado`, `lendo`, `concluido` e `abandonado`. São armazenados páginas lidas, total conhecido opcional, data de início e data de conclusão. O total pode ficar vazio quando o catálogo não informa páginas.

O percentual é calculado como páginas lidas divididas pelo total conhecido e limitado a 100. Sem total válido, a interface informa que não existe percentual calculável. O percentual é somente um indicador de páginas lidas; não representa a confiança do OCR.

## Rotas e regras

- `GET /api/library/<UUID>/progress` consulta o progresso da associação e exige autenticação. Uma associação de outra conta retorna 404; ausência de registro retorna os padrões `nao_iniciado`, zero páginas e datas vazias.
- `PUT /api/library/<UUID>/progress` cria ou atualiza progresso com CSRF. A conta vem da sessão Flask; o navegador não envia proprietário.

O backend rejeita status desconhecido, campos extras, tipos não inteiros e booleanos no lugar de números, páginas negativas, páginas lidas acima do total, datas ISO impossíveis, datas futuras, conclusão anterior ao início e data de conclusão em status não concluído. O estado `lendo` registra a data atual como início quando nenhuma data é informada. O estado `concluido` registra data de conclusão e, quando há total conhecido, ajusta as páginas lidas ao total. `nao_iniciado` não aceita páginas lidas nem data de início. Timestamps de data são armazenados à meia-noite UTC; os limites de metas são datas de calendário inclusivas.

## Integração

`templates/index.html` define os campos `#progress-status`, `#progress-pages-read`, `#progress-total-pages`, `#progress-started` e `#progress-completed` dentro de `#book-details-dialog`. `static/style.css` organiza os campos e mostra indicadores. `static/app.js` preenche os campos ao abrir detalhes, envia `PUT` com token CSRF e atualiza lista/metas após sucesso. `backend/routes.py` valida o payload e usa `backend.repositories.progresso.salvar_progresso` e `obter_progresso`; o escopo da associação é conferido por `usuario_id`. `backend/models.py` já define status, chaves e CHECKs necessários; não foi criada migração.

Os cards apresentam o status atual e, quando o total existe, uma barra acessível com páginas e percentual. O diálogo permite alterar os valores. Remover a associação de biblioteca remove seu progresso no mesmo fluxo existente, sem apagar registros bibliográficos compartilhados.

## Testes

Os testes de rota e PostgreSQL cobrem criação, atualização, percentual, conclusão, datas inválidas ou futuras, limite de páginas, CSRF, ausência de sessão e tentativa de acesso por outra conta. A suíte completa e a validação visual final estão registradas em `docs/TESTES.md`.
