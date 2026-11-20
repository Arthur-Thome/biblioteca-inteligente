# O script valida a identidade dos processos antes de solicitar paradas seguras.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PidFile = Join-Path $ProjectRoot "runtime\flask-process.json"
$VenvConfig = Join-Path $ProjectRoot ".venv\pyvenv.cfg"
$BasePython = $Python
if (Test-Path $VenvConfig) {
    $HomeLine = Get-Content -LiteralPath $VenvConfig | Where-Object { $_ -like "home = *" } | Select-Object -First 1
    if ($HomeLine) { $BasePython = Join-Path ($HomeLine.Substring(7).Trim()) "python.exe" }
}

if (Test-Path $PidFile) {
    $Record = Get-Content -LiteralPath $PidFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $Process = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if ($Process) {
        $ExpectedPython = [IO.Path]::GetFullPath($Python)
        $RecordedPython = [IO.Path]::GetFullPath($Record.python_executable)
        $InterpreterMatches = ($RecordedPython -eq $ExpectedPython -or $RecordedPython -eq $BasePython)
        $RecordedStart = [DateTimeOffset]::Parse($Record.started_at_utc).UtcDateTime
        $ActualStart = $Process.StartTime.ToUniversalTime()
        $AgeDifference = [Math]::Abs(($ActualStart - $RecordedStart).TotalSeconds)
        if ($Process.Path -ne $BasePython -or $Record.project_root -ne $ProjectRoot -or !$InterpreterMatches -or $AgeDifference -gt 20) {
            throw "O PID registrado não corresponde ao gerenciador Flask atual; o processo foi preservado."
        }
        & $Python (Join-Path $PSScriptRoot "parar_flask.py") ([string]$Record.pid)
        if ($LASTEXITCODE -ne 0) { throw "O evento de parada graciosa não foi enviado; o PostgreSQL permanece ativo." }
        Wait-Process -Id ([int]$Record.pid) -Timeout 30 -ErrorAction Stop
        Write-Output "O servidor Flask do projeto encerrou normalmente."
    }
    else {
        Write-Output "O processo Flask registrado já estava encerrado."
    }
}
else {
    Write-Output "Não há registro ativo do servidor Flask do projeto."
}

& (Join-Path $PSScriptRoot "parar_postgres.ps1")
Write-Output "A rotina de encerramento do projeto foi concluída."
