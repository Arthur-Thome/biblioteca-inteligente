# Plano de migração proposto

Este plano propõe etapas futuras sem executá-las. A implementação deve preservar o protótipo funcional e validar cada mudança antes de remover qualquer fluxo existente.

## Preparação concluída na Etapa 2

A separação inicial de responsabilidades foi realizada em `backend/`: fábrica Flask, rotas, catálogo, visão computacional, recomendações e validações. O fluxo atual permanece baseado em `localStorage`, sem PostgreSQL ou autenticação. A migração futura deverá começar dessa estrutura e preservar a chave `estante-livros-v1`; não há exportação/importação implementada. Os resultados de validação da refatoração estão em `docs/TESTES.md`.

## Direção arquitetural

Separar responsabilidades gradualmente, mantendo Flask como aplicação web:

```text
app.py / fábrica da aplicação
  -> blueprints de páginas, autenticação, livros, leitura e recomendações
  -> serviços: OCR, catálogo, biblioteca e recomendações
  -> repositórios e modelos PostgreSQL
  -> templates + CSS + JavaScript
```

Estrutura possível, a confirmar após inventário das dependências:

```text
app/ __init__.py, config.py
app/routes/ auth.py, books.py, scan.py, reading.py, recommendations.py
app/services/ ocr.py, catalog.py, matching.py, recommendations.py
app/models/ account.py, book.py, library_item.py, reading_goal.py, preference.py
app/repositories/ ...
templates/ static/ tests/ migrations/ scripts/ docs/
```

O catálogo e o OCR devem permanecer encapsulados em serviços para que a interface não dependa de detalhes dos provedores. O mapa de integração deve ser atualizado com os nomes reais de templates, IDs/classes, scripts, rotas, funções, tabelas/APIs e atualizações de DOM a cada funcionalidade integrada.

## Sequência recomendada

1. **Confirmar requisitos acadêmicos e inventário**: obter o PDF do roteiro; alinhar com o grupo a ODS/meta, problema, público, indicadores e contribuições reais; revisar o inventário e os dados locais do navegador. Não afirmar impacto na alfabetização sem evidência.
2. **Preparar versionamento seguro**: inicializar Git somente após inspeção e consentimento do responsável, adicionar `.gitignore` para `.venv`, `.env`, modelos, caches, bancos, uploads e backups, e criar `.env.example` sem valores reais. Revisar staged files antes de qualquer publicação. O remoto planejado deve ser privado; nenhuma publicação integra esta etapa.
3. **Estabilizar a base existente**: organizar funções atuais em módulos sem alterar os contratos de API; completar docstrings e comentários didáticos, validações de JSON/upload, configuração e mensagens de erro; executar e registrar testes existentes quando autorizado na etapa de implementação.
4. **Planejar PostgreSQL local**: selecionar driver/ORM e ferramenta de migração, definir configuração local, vincular host a loopback, especificar políticas de backup/restauração e validar dependências para Python 3.12/Windows. Não substituir o `localStorage` antes de existir importação validada e backup recuperável.
5. **Modelar dados e migrações**: desenhar contas, livros bibliográficos, itens de biblioteca por usuário, progresso, metas e preferências; definir chaves estrangeiras, unicidade, índices, timestamps e regras de exclusão. Preparar migrações reversíveis e teste de backup/restauração.
6. **Adicionar autenticação e autorização**: hash de senha com biblioteca apropriada, sessões seguras, proteção CSRF para operações mutáveis, validação de entrada, limites de tentativa e isolamento por proprietário. Cada rota de biblioteca deve obter usuário da sessão, nunca confiar em `user_id` do navegador.
7. **Migrar biblioteca e progresso**: criar uma exportação local explícita do navegador, permitir importação validada para a conta escolhida, tratar duplicatas e oferecer relatório de itens rejeitados. Confirmar contagens e integridade antes de considerar a migração concluída; conservar cópia recuperável até validação do grupo.
8. **Evoluir recursos**: implementar cadastro/edição de livros, acompanhamento de páginas/percentual, metas e preferências por rotas autenticadas e serviços; manter OCR e busca manual como caminhos complementares.
9. **Reforçar recomendações e demonstração**: manter explicável a recomendação atual por assuntos, avaliar qualidade com amostras documentadas e não rotular como modelo preditivo sem justificativa. Adicionar catálogo/dados locais de demonstração e modelos OCR locais para reduzir dependência de rede, respeitando licenças e limites de redistribuição.
10. **Preparar execução Windows**: fornecer scripts idempotentes para verificar configuração e dependências, iniciar PostgreSQL local, iniciar Flask, abrir navegador, encerrar apenas processos criados pelo projeto e executar backup. Scripts devem recusar operações destrutivas por padrão e nunca remover dados automaticamente.
11. **Validar ponta a ponta**: revisar segurança, integração HTML/CSS/JS/Python/banco, acessibilidade e responsividade; executar testes unitários, integração, migração, backup/restauração e apresentação local. Registrar exatamente o que foi executado e corrigir falhas críticas antes de declarar conclusão.
12. **Documentar e publicar quando autorizado**: atualizar README com tecnologias, configuração exemplificativa, instalação, execução, backup, limitações e fluxo de dados; incluir testes e documentação. Revisar segredos e arquivos incluídos, criar repositório remoto privado e fazer push somente após autenticação e autorização apropriadas.

## Dados a preservar e critérios de segurança

O protótipo guarda a coleção em `localStorage` sob a chave `estante-livros-v1`; não existe mecanismo de exportação/importação no código atual. A migração deverá preservar identificadores Open Library e metadados existentes, apresentar contagens antes/depois e rejeições, e evitar apagar ou sobrescrever a coleção do navegador até confirmação de cópia válida.

O PostgreSQL definitivo deve escutar somente localmente. Credenciais devem ficar fora do Git, com `.env.example` contendo apenas nomes e exemplos fictícios. Backups devem ser locais, protegidos e excluídos do controle de versão. A instalação e os scripts não devem inicializar, limpar ou recriar um banco sem confirmação explícita e backup verificado.

## Bloqueios e decisões pendentes

- PDF do professor indisponível; exigências adicionais precisam ser verificadas.
- O grupo ainda precisa confirmar recorte da ODS 4/meta 4.6 e indicadores compatíveis com o alcance do sistema.
- Participação dos integrantes precisa ser documentada com base em contribuições reais.
- O projeto ainda não aparece como repositório Git nesta pasta; estado de remoto/autenticação não foi avaliado.
- Driver/ORM, método de autenticação, ferramenta de migração e forma de empacotar PostgreSQL/modelos locais permanecem decisões de implementação.
- A qualidade do OCR necessita avaliação com imagens de referência; nenhum teste real foi executado nesta etapa.
