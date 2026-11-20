# O script solicita a parada smart somente ao cluster identificado do projeto.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PostgresRoot = Join-Path $ProjectRoot "postgres"
$Data = Join-Path $PostgresRoot "data"
$Runtime = Join-Path (Join-Path $PostgresRoot "runtime") "bin"
$Ctl = Join-Path $Runtime "pg_ctl.exe"
$Ready = Join-Path $Runtime "pg_isready.exe"
$Marker = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CLUSTER"
$Configured = Join-Path $Data "BIBLIOTECA_INTELIGENTE_CONFIGURED"

if (!(Test-Path $Ctl) -or !(Test-Path (Join-Path $Data "PG_VERSION"))) {
    Write-Output "O cluster local do projeto não está inicializado."
    exit 0
}
if (!(Test-Path $Marker) -or !(Test-Path $Configured)) {
    throw "O marcador do cluster do projeto está ausente; nenhum processo foi encerrado."
}
& $Ready -h 127.0.0.1 -p 5433 -t 5 *> $null
$AcceptingConnections = ($LASTEXITCODE -eq 0)
if (!$AcceptingConnections) {
    & $Ctl -D $Data status *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Output "O cluster PostgreSQL do projeto já estava parado."
        exit 0
    }
    throw "O cluster aparece ativo, mas não aceitou conexões; nenhum processo foi encerrado."
}
$Verifier = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Verifier)) { throw "O ambiente virtual não foi encontrado para validar a instância ativa." }
& $Verifier (Join-Path $ProjectRoot "scripts\configurar_postgres.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "A porta 5433 não corresponde à instância PostgreSQL do projeto; nenhum processo foi encerrado."
}
& $Ctl -D $Data -m smart -w -t 45 stop
if ($LASTEXITCODE -ne 0) {
    throw "A parada segura não foi confirmada; nenhum encerramento forçado foi tentado."
}
& $Ready -h 127.0.0.1 -p 5433 -t 5 *> $null
if ($LASTEXITCODE -eq 0) {
    throw "O cluster ainda aparece ativo após a solicitação de parada segura."
}
Write-Output "O cluster PostgreSQL do projeto encerrou de forma segura."
