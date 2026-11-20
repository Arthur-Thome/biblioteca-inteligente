# O script inicia apenas o cluster PostgreSQL identificado como pertencente ao projeto.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PostgresRoot = Join-Path $ProjectRoot "postgres"
$Runtime = Join-Path (Join-Path $PostgresRoot "runtime") "bin"
$Data = Join-Path $PostgresRoot "data"
$Logs = Join-Path $PostgresRoot "logs"
$Ctl = Join-Path $Runtime "pg_ctl.exe"
$Ready = Join-Path $Runtime "pg_isready.exe"
$Marker = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CLUSTER"
$Configured = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CONFIGURED"

if (!(Test-Path $Ctl) -or !(Test-Path $Ready)) {
    throw "Os executáveis PostgreSQL locais não foram encontrados; execute a preparação do ambiente."
}
if (!(Test-Path (Join-Path $Data "PG_VERSION"))) {
    throw "O cluster ainda não foi inicializado; execute a preparação do ambiente."
}
if (!(Test-Path $Marker) -or !(Test-Path $Configured)) {
    throw "O diretório não está identificado como cluster configurado do projeto; os dados foram preservados."
}
$Version = (Get-Content -LiteralPath (Join-Path $Data "PG_VERSION") -Raw).Trim()
if ($Version -ne "17") {
    throw "A pasta de dados contém PostgreSQL $Version, não PostgreSQL 17."
}
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

& $Ctl -D $Data status *> $null
$CtlReportsRunning = ($LASTEXITCODE -eq 0)
$ReadyCode = 1
& $Ready -h 127.0.0.1 -p 5433 -t 5 *> $null
$ReadyCode = $LASTEXITCODE
$Listener = @(Get-NetTCPConnection -State Listen -LocalPort 5433 -ErrorAction SilentlyContinue)
if ($ReadyCode -eq 0) {
    $Verifier = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (!(Test-Path $Verifier)) { throw "O ambiente virtual não foi encontrado para validar a instância ativa." }
    & $Verifier (Join-Path $ProjectRoot "scripts\configurar_postgres.py") --check
    if ($LASTEXITCODE -ne 0) {
        throw "A porta 5433 respondeu, mas a instância não corresponde ao cluster local verificado do projeto."
    }
    Write-Output "A instância PostgreSQL do projeto já estava ativa e autenticada em 127.0.0.1:5433."
    exit 0
}
if ($CtlReportsRunning) {
    throw "O cluster do projeto aparece ativo, mas não aceitou conexões em 127.0.0.1:5433."
}
if ($Listener.Count -gt 0) {
    $Owners = ($Listener | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
    throw "A porta 5433 está ocupada pelo processo $Owners; nenhum processo foi encerrado."
}

$LogFile = Join-Path $Logs "postgres-startup.log"
& $Ctl -D $Data -l $LogFile -w -t 60 start
if ($LASTEXITCODE -ne 0) {
    throw "O PostgreSQL do projeto não iniciou; consulte o log local de inicialização."
}
& $Ready -h 127.0.0.1 -p 5433 -t 10 *> $null
if ($LASTEXITCODE -ne 0) {
    throw "O PostgreSQL foi solicitado, mas a verificação de disponibilidade falhou."
}
& (Join-Path $ProjectRoot ".venv\Scripts\python.exe") (Join-Path $ProjectRoot "scripts\configurar_postgres.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "O servidor respondeu, mas a autenticação ou identificação do cluster do projeto falhou."
}
Write-Output "PostgreSQL 17 respondeu em 127.0.0.1:5433."
