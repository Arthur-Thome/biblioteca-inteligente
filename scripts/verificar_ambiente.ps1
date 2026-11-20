# O script diferencia componentes instalados, configurados, iniciados e funcionais.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PgBin = Join-Path (Join-Path $ProjectRoot "postgres") "runtime\bin"
$Data = Join-Path (Join-Path $ProjectRoot "postgres") "data"
$EnvFile = Join-Path $ProjectRoot ".env"
$Problems = 0

function Show-Check {
    # A função informa o estado observado e contabiliza somente falhas reais.
    param([string]$Name, [string]$State, [bool]$Ok)
    if ($Ok) { Write-Output ("[OK]   {0}: {1}" -f $Name, $State) }
    else { Write-Output ("[PEND] {0}: {1}" -f $Name, $State); $script:Problems++ }
}

$PythonVersion = "ausente"
if (Test-Path $Python) { $PythonVersion = (& $Python --version 2>&1 | Out-String).Trim() }
Show-Check "Python" $PythonVersion ($PythonVersion -match "^Python 3\.12\.")
if (Test-Path $Python) {
    Show-Check "Ambiente virtual" ".venv presente" $true
    & $Python -m pip check *> $null
    $DependenciesOk = ($LASTEXITCODE -eq 0)
    $DependencyState = "pip check aprovado"
    if (!$DependenciesOk) { $DependencyState = "pip check encontrou conflito" }
    Show-Check "Dependências Python" $DependencyState $DependenciesOk
    & $Python -c "import flask, rapidocr, psycopg, sqlalchemy, alembic" *> $null
    $ImportsOk = ($LASTEXITCODE -eq 0)
    $ImportState = "Flask, RapidOCR, Psycopg, SQLAlchemy e Alembic importáveis"
    if (!$ImportsOk) { $ImportState = "uma ou mais dependências estão ausentes" }
    Show-Check "Dependências principais" $ImportState $ImportsOk
}
else {
    Show-Check "Ambiente virtual" "ausente" $false
}

$Postgres = Join-Path $PgBin "postgres.exe"
$PgVersion = "binários locais ausentes"
if (Test-Path $Postgres) { $PgVersion = (& $Postgres --version 2>&1 | Out-String).Trim() }
Show-Check "Binários PostgreSQL" $PgVersion ($PgVersion -match "PostgreSQL\) 17\.")
$Cluster = (Test-Path (Join-Path $Data "PG_VERSION")) -and (Test-Path (Join-Path $Data "BIBLIOTECA_INTELIGENTE_CONFIGURED"))
$ClusterState = "não inicializado"
if ($Cluster) { $ClusterState = "inicializado e marcado pelo projeto" }
Show-Check "Cluster local" $ClusterState $Cluster
$EnvState = "ausente"
if (Test-Path $EnvFile) { $EnvState = "presente; valores confidenciais omitidos" }
Show-Check "Configuração local" $EnvState (Test-Path $EnvFile)

$Ready = $false
if ($Cluster -and (Test-Path (Join-Path $PgBin "pg_isready.exe"))) {
    & (Join-Path $PgBin "pg_isready.exe") -h 127.0.0.1 -p 5433 -t 5 *> $null
    $Ready = ($LASTEXITCODE -eq 0)
}
if ($Ready) {
    Show-Check "PostgreSQL iniciado" "aceitando conexões em 127.0.0.1:5433" $true
    if ((Test-Path $Python) -and (Test-Path $EnvFile)) {
        & $Python (Join-Path $PSScriptRoot "configurar_postgres.py") --check
        $AuthOk = ($LASTEXITCODE -eq 0)
        $AuthState = "instância do projeto, SCRAM e role restrita aprovadas"
        if (!$AuthOk) { $AuthState = "instância ou privilégios não passaram na verificação" }
        Show-Check "Autenticação e instância PostgreSQL" $AuthState $AuthOk
        Show-Check "Interface de rede PostgreSQL" "somente 127.0.0.1:5433; diretório local do projeto confirmado" $AuthOk
        if ($AuthOk) {
            $MigrationOutput = (& $Python (Join-Path $PSScriptRoot "verificar_migracoes.py") | Out-String).Trim()
            $MigrationOk = ($LASTEXITCODE -eq 0)
            $MigrationState = $MigrationOutput
            if (!$MigrationOk) { $MigrationState = "revisão ausente, desatualizada ou inacessível" }
            Show-Check "Migrações do banco principal" $MigrationState $MigrationOk
        }
    }
}
else {
    Show-Check "PostgreSQL iniciado" "configurado, mas parado" $true
}

$ModelFiles = @("PP-OCRv6_det_small.onnx", "ch_ppocr_mobile_v2.0_cls_mobile.onnx", "PP-OCRv6_rec_small.onnx")
$MissingModels = @($ModelFiles | Where-Object { !(Test-Path (Join-Path (Join-Path $ProjectRoot "models_ocr") $_)) })
$ModelState = "3 arquivos locais presentes"
if ($MissingModels.Count -gt 0) { $ModelState = "ausentes: $($MissingModels -join ', ')" }
Show-Check "Modelos OCR" $ModelState ($MissingModels.Count -eq 0)
if ($MissingModels.Count -eq 0 -and (Test-Path $Python)) {
    & $Python (Join-Path $PSScriptRoot "verificar_ocr.py")
    $OcrOk = ($LASTEXITCODE -eq 0)
    $OcrState = "inferência local sem rede aprovada"
    if (!$OcrOk) { $OcrState = "modelo ou inferência falhou" }
    Show-Check "Funcionamento OCR" $OcrState $OcrOk
}

$AppState = "parado"
if (Test-Path $Python) {
    $AppState = (& $Python (Join-Path $PSScriptRoot "verificar_flask.py") | Out-String).Trim()
    $AppExitCode = $LASTEXITCODE
    if ($AppExitCode -eq 2) { $AppState = "parado (não iniciado)" }
    $AppOk = ($AppExitCode -eq 0 -or $AppExitCode -eq 2)
}
else {
    $AppOk = $false
}
Show-Check "Aplicação Flask" $AppState $AppOk

$RequiredFiles = @("app.py", "backend\__init__.py", "backend\routes.py", "backend\database.py", "backend\models.py", "migrations\env.py", "alembic.ini", "scripts\verificar_migracoes.py", "scripts\verificar_flask.py", "templates\index.html", "static\style.css", "static\app.js", "requirements.txt")
$MissingFiles = @($RequiredFiles | Where-Object { !(Test-Path (Join-Path $ProjectRoot $_)) })
$FilesState = "estrutura essencial verificada"
if ($MissingFiles.Count -gt 0) { $FilesState = "ausentes: $($MissingFiles -join ', ')" }
Show-Check "Arquivos essenciais" $FilesState ($MissingFiles.Count -eq 0)

if ($Problems -gt 0) { exit 1 }
Write-Output "Verificação concluída; estados instalado, configurado, iniciado e funcional foram diferenciados."
