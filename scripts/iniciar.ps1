# O script confirma configuração e saúde local antes de iniciar o Flask.
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Runner = Join-Path $PSScriptRoot "executar_flask.py"
$Runtime = Join-Path $ProjectRoot "runtime"
$Logs = Join-Path $ProjectRoot "logs"
$VenvConfig = Join-Path $ProjectRoot ".venv\pyvenv.cfg"
$BasePython = $Python
if (Test-Path $VenvConfig) {
    $HomeLine = Get-Content -LiteralPath $VenvConfig | Where-Object { $_ -like "home = *" } | Select-Object -First 1
    if ($HomeLine) { $BasePython = Join-Path ($HomeLine.Substring(7).Trim()) "python.exe" }
}

function Abrir-NavegadorLocal {
    <# O procedimento abre o endereço local no Microsoft Edge ou no navegador padrão.

    Parâmetros:
        Endereco: endereço HTTP local já verificado pela rotina de inicialização.

    Retorno:
        Nenhum; o processo do navegador é iniciado sem bloquear o servidor Flask.

    Tratamento de erros:
        Uma falha de associação do navegador é informada sem declarar a aplicação
        indisponível, pois a saúde HTTP já foi confirmada separadamente.
    #>
    param([Parameter(Mandatory = $true)][string]$Endereco)
    $Candidatos = @()
    if (${env:ProgramFiles(x86)}) {
        $Candidatos += Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"
    }
    if ($env:ProgramFiles) {
        $Candidatos += Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"
    }
    $Navegador = $Candidatos | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    try {
        if ($Navegador) {
            Start-Process -FilePath $Navegador -ArgumentList @("--new-window", $Endereco)
        }
        else {
            Start-Process -FilePath $Endereco
        }
    }
    catch {
        Write-Warning "O servidor está disponível, mas o navegador não pôde ser aberto automaticamente. Endereço: $Endereco"
    }
}

if (!(Test-Path $Python)) { throw "O Python do ambiente .venv não foi encontrado." }
if (!(Test-Path (Join-Path $ProjectRoot ".env"))) { throw "A configuração local não existe; execute scripts\instalar_ambiente.ps1." }
New-Item -ItemType Directory -Force -Path $Runtime, $Logs | Out-Null
& (Join-Path $PSScriptRoot "iniciar_postgres.ps1")
& $Python (Join-Path $PSScriptRoot "configurar_postgres.py") --check
if ($LASTEXITCODE -ne 0) { throw "A autenticação PostgreSQL da aplicação não foi confirmada." }

$PidFile = Join-Path $Runtime "flask-process.json"
if (Test-Path $PidFile) {
    try {
        $Record = Get-Content -LiteralPath $PidFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $Existing = Get-Process -Id ([int]$Record.pid) -ErrorAction Stop
        $ExpectedPython = [IO.Path]::GetFullPath($Python)
        $RecordedPython = [IO.Path]::GetFullPath($Record.python_executable)
        $InterpreterMatches = ($RecordedPython -eq $ExpectedPython -or $RecordedPython -eq $BasePython)
        if ($Existing.Path -eq $BasePython -and $Record.project_root -eq $ProjectRoot -and $InterpreterMatches) {
            & $Python -c "import requests,sys; response=requests.get('http://127.0.0.1:5000/api/health',timeout=5); sys.exit(0 if response.status_code==200 else 1)" *> $null
            if ($LASTEXITCODE -eq 0) {
                Write-Output "O servidor Flask do projeto já estava ativo."
                Abrir-NavegadorLocal -Endereco "http://127.0.0.1:5000"
                exit 0
            }
        }
    }
    catch {
        # O registro antigo não autoriza encerrar ou remover processos.
    }
}

$Listener = @(Get-NetTCPConnection -State Listen -LocalPort 5000 -ErrorAction SilentlyContinue)
if ($Listener.Count -gt 0) {
    $Owners = ($Listener | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
    throw "A porta 5000 já está ocupada pelo processo $Owners; nenhum processo foi encerrado."
}

$Stdout = Join-Path $Logs "flask-output.log"
$Stderr = Join-Path $Logs "flask-error.log"
$Arguments = '"' + $Runner + '"'
$Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr -PassThru
$Ready = $false
for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
    Start-Sleep -Seconds 1
    if ($Process.HasExited) { throw "O processo Flask encerrou durante a inicialização; consulte logs\flask-error.log." }
    try {
        & $Python -c "import requests,sys; response=requests.get('http://127.0.0.1:5000/api/health',timeout=2); sys.exit(0 if response.status_code==200 else 1)" *> $null
        if ($LASTEXITCODE -eq 0) { $Ready = $true; break }
    }
    catch {
        # A tentativa repete a verificação enquanto o servidor conclui a inicialização.
    }
}
if (!$Ready) {
    throw "A página de saúde não respondeu no prazo; o servidor não será declarado iniciado."
}
Write-Output "Flask e PostgreSQL responderam em endereços locais."
Abrir-NavegadorLocal -Endereco "http://127.0.0.1:5000"
