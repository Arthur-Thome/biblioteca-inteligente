# O script prepara dependências locais sem substituir clusters ou credenciais existentes.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Data = Join-Path $ProjectRoot "postgres\data"
$Bin = Join-Path $ProjectRoot "postgres\runtime\bin"
$EnvFile = Join-Path $ProjectRoot ".env"
$ModelSource = Join-Path $ProjectRoot ".venv\Lib\site-packages\rapidocr\models"
$ModelTarget = Join-Path $ProjectRoot "models_ocr"

function New-LocalSecret {
    # A função obtém entropia criptográfica e retorna somente uma sequência hexadecimal.
    $Bytes = New-Object byte[] 32
    $Generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $Generator.GetBytes($Bytes)
        return ([BitConverter]::ToString($Bytes)).Replace("-", "")
    }
    finally {
        $Generator.Dispose()
        [Array]::Clear($Bytes, 0, $Bytes.Length)
    }
}

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or ($env:PROCESSOR_ARCHITECTURE -ne "AMD64" -and $env:PROCESSOR_ARCHITEW6432 -ne "AMD64")) {
    throw "Esta distribuição PostgreSQL requer Windows x64."
}
if (!(Test-Path (Join-Path $Bin "initdb.exe"))) {
    throw "O ZIP PostgreSQL 17 não foi extraído para postgres\runtime."
}
if (!(Test-Path $Python)) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if (!$Launcher) { throw "Python 3.12 não está disponível para preparar .venv." }
    & py -3.12 -m venv (Join-Path $ProjectRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "A criação do ambiente virtual falhou." }
}
$PythonVersion = (& $Python --version 2>&1 | Out-String).Trim()
if ($PythonVersion -notmatch "^Python 3\.12\.") {
    throw "O ambiente virtual precisa usar Python 3.12; versão encontrada: $PythonVersion."
}

Write-Output "Verificando as dependências exclusivamente no ambiente virtual..."
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "A instalação de dependências no .venv falhou." }

New-Item -ItemType Directory -Force -Path $ModelTarget | Out-Null
foreach ($Name in @("PP-OCRv6_det_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx", "PP-OCRv6_rec_small.onnx")) {
    $Target = Join-Path $ModelTarget $Name
    if (!(Test-Path $Target)) {
        $Source = Join-Path $ModelSource $Name
        if (!(Test-Path $Source)) { throw "O pacote RapidOCR não contém o modelo local esperado: $Name." }
        Copy-Item -LiteralPath $Source -Destination $Target
    }
}

New-Item -ItemType Directory -Force -Path $Data, (Join-Path $ProjectRoot "postgres\logs"), (Join-Path $ProjectRoot "postgres\backups"), (Join-Path $ProjectRoot "runtime"), (Join-Path $ProjectRoot "logs") | Out-Null
$Items = @(Get-ChildItem -LiteralPath $Data -Force -ErrorAction SilentlyContinue)
$HasCluster = Test-Path (Join-Path $Data "PG_VERSION")
$ClusterMarker = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CLUSTER"
$ConfiguredMarker = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CONFIGURED"

if ($HasCluster -and !(Test-Path $ClusterMarker)) {
    throw "Já existe um cluster sem marcador do projeto; ele foi preservado e não será inicializado nem reconfigurado."
}
if (!$HasCluster -and $Items.Count -gt 0) {
    throw "O diretório de dados contém arquivos sem uma instância reconhecida; nenhum arquivo foi alterado."
}
if ($HasCluster -and !(Test-Path $EnvFile)) {
    throw "O cluster já existe, mas .env está ausente. As credenciais existentes não serão substituídas."
}

if (!(Test-Path $EnvFile)) {
    $AdminPassword = New-LocalSecret
    $AppPassword = New-LocalSecret
    $Content = @(
        "POSTGRES_HOST=127.0.0.1"
        "POSTGRES_PORT=5433"
        "POSTGRES_ADMIN_USER=postgres"
        "POSTGRES_ADMIN_PASSWORD=$AdminPassword"
        "POSTGRES_APP_USER=biblioteca_app"
        "POSTGRES_APP_PASSWORD=$AppPassword"
        "POSTGRES_DB=biblioteca_inteligente"
        "DATABASE_URL="
        "BIBLIOTECA_SECRET_KEY=$(New-LocalSecret)"
    ) -join [Environment]::NewLine
    [IO.File]::WriteAllText($EnvFile, $Content, [Text.UTF8Encoding]::new($false))
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $ProjectOwner = (Get-Acl $ProjectRoot).Owner
    $GrantIdentities = @($Identity)
    if ($ProjectOwner -and $ProjectOwner -ne $Identity) { $GrantIdentities += $ProjectOwner }
    $GrantRules = @($GrantIdentities | ForEach-Object { $_ + ":(F)" })
    & icacls.exe $EnvFile /inheritance:r /grant:r $GrantRules *> $null
    if ($LASTEXITCODE -ne 0) { throw "As permissões locais do arquivo .env não puderam ser restringidas." }
    $AdminPassword = $null
    $AppPassword = $null
    $Content = $null
    Write-Output "As credenciais locais foram geradas e gravadas no arquivo .env protegido."
}

# Uma instalação anterior recebe uma chave de sessão persistente sem substituir credenciais.
$EnvContent = [IO.File]::ReadAllText($EnvFile)
if ($EnvContent -notmatch '(?m)^BIBLIOTECA_SECRET_KEY=\S+') {
    $SessionKey = New-LocalSecret
    $EnvContent = $EnvContent.TrimEnd() + [Environment]::NewLine + "BIBLIOTECA_SECRET_KEY=$SessionKey" + [Environment]::NewLine
    [IO.File]::WriteAllText($EnvFile, $EnvContent, [Text.UTF8Encoding]::new($false))
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $EnvFile /inheritance:r /grant:r ($Identity + ":(F)") *> $null
    if ($LASTEXITCODE -ne 0) { throw "As permissões da chave local de sessão não puderam ser restringidas." }
    $SessionKey = $null
    $EnvContent = $null
    Write-Output "A chave local de sessão foi gerada e armazenada no arquivo .env protegido."
}

if (!$HasCluster) {
    $Settings = @{}
    foreach ($Line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
        if ($Line -match "^([^#=]+)=(.*)$") { $Settings[$Matches[1]] = $Matches[2] }
    }
    foreach ($Required in @("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_ADMIN_USER", "POSTGRES_ADMIN_PASSWORD", "POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD", "POSTGRES_DB")) {
        if (!$Settings[$Required]) { throw "A configuração local não possui o campo $Required." }
    }
    if ($Settings["POSTGRES_HOST"] -ne "127.0.0.1" -or $Settings["POSTGRES_PORT"] -ne "5433") {
        throw "A configuração local não corresponde à instância exclusiva esperada."
    }

    $PwFile = Join-Path $ProjectRoot "postgres\runtime\initdb-password.tmp"
    try {
        [IO.File]::WriteAllText($PwFile, $Settings["POSTGRES_ADMIN_PASSWORD"], [Text.UTF8Encoding]::new($false))
        $Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        & icacls.exe $PwFile /inheritance:r /grant:r ($Identity + ":(F)") *> $null
        if ($LASTEXITCODE -ne 0) { throw "Não foi possível restringir o arquivo temporário de inicialização." }
        & (Join-Path $Bin "initdb.exe") "--pgdata=$Data" "--username=postgres" "--pwfile=$PwFile" "--auth-local=scram-sha-256" "--auth-host=scram-sha-256" "--encoding=UTF8"
        if ($LASTEXITCODE -ne 0) { throw "initdb falhou; os arquivos resultantes foram preservados para inspeção." }
    }
    finally {
        if (Test-Path $PwFile) { Remove-Item -LiteralPath $PwFile -Force }
    }
    if (!(Test-Path (Join-Path $Data "PG_VERSION"))) { throw "initdb não produziu um cluster verificável." }
    Set-Content -LiteralPath $ClusterMarker -Value "PostgreSQL 17 da Biblioteca Inteligente" -Encoding ASCII

    $Config = @(
        ""
        "# Configuração local da Biblioteca Inteligente."
        "listen_addresses = '127.0.0.1'"
        "port = 5433"
        "password_encryption = 'scram-sha-256'"
        "logging_collector = on"
        "log_directory = '../logs'"
        "log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'"
        "log_min_messages = warning"
    )
    Add-Content -LiteralPath (Join-Path $Data "postgresql.conf") -Value $Config -Encoding ASCII
    Set-Content -LiteralPath (Join-Path $Data "pg_hba.conf") -Encoding ASCII -Value @(
        "# A instância aceita apenas conexões locais com autenticação SCRAM."
        "local all all scram-sha-256"
        "host all all 127.0.0.1/32 scram-sha-256"
        "host all all ::1/128 scram-sha-256"
    )
    Set-Content -LiteralPath $ConfiguredMarker -Value "SCRAM-SHA-256; listen_addresses=127.0.0.1; port=5433" -Encoding ASCII
}
elseif (!(Test-Path $ConfiguredMarker)) {
    throw "O cluster do projeto não possui marcador de configuração concluída; os arquivos foram preservados para análise."
}

& (Join-Path $PSScriptRoot "iniciar_postgres.ps1")
if (!(Test-Path (Join-Path $Data "BIBLIOTECA_INTELIGENTE_CONFIGURED"))) { throw "A configuração do cluster não foi confirmada." }
& $Python (Join-Path $PSScriptRoot "configurar_postgres.py") --setup
if ($LASTEXITCODE -ne 0) { throw "A criação/verificação do banco ou da conta de aplicação falhou." }
& $Python (Join-Path $PSScriptRoot "verificar_ocr.py")
if ($LASTEXITCODE -ne 0) { throw "A verificação dos modelos OCR locais falhou." }
Write-Output "Ambiente local preparado. O servidor Flask ainda não foi iniciado."
