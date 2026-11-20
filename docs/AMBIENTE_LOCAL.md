# Ambiente local no Windows

## Escopo

O projeto utiliza Python 3.12 x64 em `.venv/` e PostgreSQL 17.12 em execução local, sem serviço permanente do Windows. O esquema PostgreSQL foi preparado e migrado, mas a aplicação Flask continua usando `localStorage` para a biblioteca e não abre conexões com o banco.

## Preparação e execução

Na primeira configuração, `scripts/instalar_ambiente.ps1` instala dependências apenas em `.venv/`, disponibiliza os modelos OCR locais, gera `.env` se ainda não existir, protege suas permissões e inicializa o cluster somente quando o diretório ainda não contém uma instância. A rotina preserva uma configuração e dados existentes.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar_ambiente.ps1
```

Após a preparação, os arquivos `INICIAR.bat`, `PARAR.bat` e `VERIFICAR.bat` chamam os scripts locais correspondentes. A inicialização verifica PostgreSQL e Flask antes de confirmar disponibilidade. A parada solicita desligamento controlado. A verificação separa componentes presentes, configurados e respondendo.

## Estrutura local

- `.venv/`: Python e dependências do projeto.
- `.env`: credenciais locais aleatórias, protegido por ACL e ignorado pelo Git.
- `postgres/runtime/`: executáveis e bibliotecas portáteis do PostgreSQL.
- `postgres/data/`: cluster e dados locais.
- `postgres/logs/`: registros do cluster.
- `postgres/backups/`: dumps datados, mantidos sem remoção automática.
- `models_ocr/`: modelos RapidOCR usados sem download em cada inicialização.

Os diretórios locais de dados, runtime, segredos e modelos não são destinados ao repositório. `.env.example` contém somente nomes de configuração e valores ilustrativos não utilizáveis como credenciais.

## Dependências de rede

A preparação inicial pode precisar de acesso ao índice de pacotes Python para instalar dependências. O OCR já configurado usa arquivos locais e foi executado com as conexões de rede bloqueadas. Pesquisas bibliográficas e recomendações dependem da Open Library e, portanto, de conectividade externa. O Flask é iniciado em `127.0.0.1:5000`; o banco fica em `127.0.0.1:5433`.

## Diagnóstico

Quando a inicialização falha, `VERIFICAR.bat` identifica dependências, arquivos, credenciais sem exibir valores, listener, autenticação, OCR e saúde HTTP. A porta 5432 pode pertencer a outra instalação PostgreSQL: a instância do projeto permanece isolada na porta 5433 e os scripts não encerram serviços externos. Se 5433 estiver ocupada, a causa deverá ser identificada antes de qualquer mudança de porta.

O navegador precisa conceder acesso à câmera. A webcam física do notebook ainda depende de homologação manual. O PostgreSQL contém somente o esquema inicial; nenhum livro ou conta real foi inserido e nenhum dado do `localStorage` é copiado ou apagado.

## Verificações realizadas

Na preparação registrada em `docs/TESTES.md`, o ambiente virtual passou pela suíte automatizada, a instância local respondeu com autenticação SCRAM, o OCR carregou os modelos locais sem internet e os scripts iniciaram e encerraram os processos do projeto. As rotas Flask continuam sem integração ao PostgreSQL.
