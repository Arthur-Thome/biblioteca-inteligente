# Cadastro, login e biblioteca autenticada

## Cadastro e armazenamento

`GET /cadastro` apresenta os campos de nome de exibição, nome de usuário e senha com confirmação. `POST /cadastro` repete a validação no servidor: nome obrigatório até 160 caracteres, usuário canônico entre 3 e 40 caracteres, senha entre 12 e 128 caracteres e confirmação coincidente. E-mail e confirmação por e-mail não são solicitados. O nome de usuário é normalizado com Unicode NFKC, espaços laterais removidos e `casefold()`; o índice único PostgreSQL impede duplicações.

`backend.routes.cadastrar` calcula o hash com `werkzeug.security.generate_password_hash` (scrypt) e delega a gravação a `backend.repositories.usuarios.criar_usuario` dentro de `session_scope`. O valor em texto puro não é persistido, incluído na sessão, resposta ou log. Após cadastro, o navegador segue para `/login`.

## Login e logout

`GET /login` mostra o formulário; `POST /login` consulta o usuário pelo nome canônico e compara o hash usando `check_password_hash`. Credenciais inválidas recebem a mesma mensagem. O controle temporário em memória limita a oito falhas por combinação de origem e usuário numa janela de dez minutos; não cria bloqueio permanente e reinicia com o processo Flask.

O login limpa o estado anterior e cria cookie Flask assinado que contém somente o UUID da conta e o token CSRF. O UUID é confirmado no PostgreSQL em cada requisição antes de ser utilizado. `POST /logout` remove a sessão após validação CSRF. A biblioteca pessoal é entregue por `GET /` somente após autenticação.

## Livros por conta

`GET /api/library` consulta o repositório com o proprietário derivado de `g.usuario.id`. `POST /api/library` valida os metadados do candidato Open Library e cria ou reutiliza o registro bibliográfico antes de associá-lo pela tabela `biblioteca_usuario`. `DELETE /api/library/<item_id>` remove somente a associação que pertence à conta; o registro bibliográfico compartilhado não é apagado.

Nenhuma rota aceita um ID de usuário para definir propriedade. A biblioteca não importa nem altera `estante-livros-v1`; a interface verifica somente se a chave está presente para apresentar uma nota de dados legados preservados.

## Rotas e respostas

| Método e rota | Acesso | Resultado |
|---|---|---|
| `GET /cadastro`, `POST /cadastro` | Público | Formulário e criação de conta; erros de entrada 400 e colisão 409 |
| `GET /login`, `POST /login` | Público | Formulário, sessão válida ou credenciais recusadas |
| `POST /logout` | Autenticado e CSRF | Remove sessão e redireciona ao login |
| `GET /` | Autenticado | Biblioteca associada à conta |
| `GET /api/library` | Autenticado | Lista JSON por proprietário |
| `POST /api/library` | Autenticado e CSRF | Associação de livro confirmado |
| `DELETE /api/library/<UUID>` | Autenticado e CSRF | Remove associação própria; item alheio retorna 404 |
| `GET /api/search`, `POST /api/recognize`, `POST /api/recommend` | Autenticado; POST também CSRF | Busca, OCR e recomendações da biblioteca própria |
| `GET /api/health` | Público | Estado resumido sem credenciais ou dados de usuários |

Todos os testes de integração que criam contas usam exclusivamente `biblioteca_inteligente_test`.
