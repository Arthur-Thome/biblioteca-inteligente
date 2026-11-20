# Plano futuro: `localStorage` para PostgreSQL

## Estado e origem dos dados

A migração não foi executada. A interface continua utilizando a chave `estante-livros-v1` do navegador. `static/app.js` lê uma lista JSON e conserva somente objetos com `id` textual; ao salvar, cada livro contém `id`, `title`, `author`, `year`, `subjects`, `cover` e `url`. A aplicação não envia essa coleção ao Flask atualmente.

O PostgreSQL já contém o esquema inicial, mas não tem cópias da biblioteca local. A leitura pelo navegador permanece intacta.

## Estratégia proposta

1. Implementar e validar autenticação individual em etapa própria; cada importação deverá usar o UUID da conta autenticada no servidor.
2. Solicitar consentimento explícito antes de ler ou enviar a coleção. O servidor não deve confiar em `usuario_id` fornecido no corpo da requisição.
3. Oferecer exportação JSON local e cópia de segurança antes da importação. A chave original deverá permanecer disponível até conferência e aceite do resultado.
4. Validar o array e cada campo, ignorar valores malformados sem removê-los do navegador e apresentar um relatório de itens aceitos, duplicados e pendentes.
5. Mapear `title` para `livros.titulo`, `author` para `autores`, `year` para `ano_publicacao`, `subjects` para `assuntos`, `cover` para `url_capa` e `url` para referência externa. O identificador antigo deverá ser preservado como `identificador_externo` somente quando sua origem puder ser identificada; caso contrário, será preservado em um registro de importação/versionamento planejado, sem presumir que seja ISBN ou ID Open Library.
6. Identificar duplicatas primeiro por origem + ID externo e, quando disponível, por ISBN normalizado. Título e autor semelhantes devem apenas gerar sugestão de revisão: registros com mesmo título podem ser edições diferentes.
7. Executar uma simulação sem gravar dados, mostrar o mapeamento e solicitar confirmação. A importação confirmada deverá ocorrer em transação por conta, com rastreio de cada identificador antigo para manter idempotência.
8. Conferir contagem, vínculos do usuário, metadados e IDs mapeados após commit. Itens ambíguos ou incompletos devem permanecer no navegador para decisão posterior.
9. Manter leitura dupla temporária somente se houver plano claro de sincronização; não apagar nem desativar a chave local até confirmação e backup exportado.

## Preservação e retorno

A importação deve ser reversível por usuário por meio do relatório de mapeamento e de exportação original. Uma falha antes do commit deve reverter a transação. Uma falha depois do commit não deve limpar `localStorage`; a comparação e a correção devem ocorrer antes de qualquer remoção. Nenhuma restauração deve sobrescrever o banco principal sem procedimento separado.

## Decisões ainda necessárias

- Regra para registros sem origem bibliográfica identificável.
- Política para capas externas e URLs expiradas.
- Critérios de aceitação e apresentação do consentimento.
- Aprovação do grupo antes de desativar o armazenamento do navegador.

## Estado após a Etapa 5

O sistema agora utiliza PostgreSQL para contas e novos livros associados a cada conta autenticada. A chave `estante-livros-v1` permanece preservada; o JavaScript só consulta se a chave existe para exibir a nota de que os itens antigos não foram importados. O conteúdo não foi lido, alterado, enviado nem associado a uma conta. A importação opcional continua pendente e exige prévia e confirmação explícita conforme o procedimento acima.
