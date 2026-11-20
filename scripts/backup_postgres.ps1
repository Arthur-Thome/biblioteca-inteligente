# O script cria um dump datado e preserva backups anteriores.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvFile = Join-Path $ProjectRoot ".env"
$Dump = Join-Path $ProjectRoot "postgres\runtime\bin\pg_dump.exe"
$BackupDir = Join-Path $ProjectRoot "postgres\backups"
if (!(Test-Path $EnvFile)) { throw "A configuração .env não foi encontrada." }
if (!(Test-Path $Dump)) { throw "pg_dump não foi encontrado na distribuição local." }

$Settings = @{}
foreach ($Line in Get-Content -LiteralPath $EnvFile -Encoding UTF8) {
    if ($Line -match "^([^#=]+)=(.*)$") { $Settings[$Matches[1]] = $Matches[2] }
}
foreach ($Required in @("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD", "POSTGRES_DB")) {
    if (!$Settings[$Required]) { throw "A configuração local não possui o campo $Required." }
}
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Target = Join-Path $BackupDir "biblioteca_inteligente-$Timestamp.dump"
if (Test-Path $Target) { throw "O arquivo de backup já existe; nenhum arquivo foi substituído." }
$PreviousPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $Settings["POSTGRES_APP_PASSWORD"]
    & $Dump --host $Settings["POSTGRES_HOST"] --port $Settings["POSTGRES_PORT"] --username $Settings["POSTGRES_APP_USER"] --dbname $Settings["POSTGRES_DB"] --format=custom --no-owner --no-privileges --file $Target
    if ($LASTEXITCODE -ne 0 -or !(Test-Path $Target) -or (Get-Item $Target).Length -eq 0) {
        throw "pg_dump não confirmou a criação de um backup válido."
    }
}
finally {
    $env:PGPASSWORD = $PreviousPassword
}
Write-Output "Backup local concluído: $Target"
