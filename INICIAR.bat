@echo off
rem O iniciador encaminha a inicializacao dos servicos locais ao PowerShell do projeto.
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar.ps1"
if errorlevel 1 (
    echo.
    echo A inicializacao nao foi confirmada. Consulte a mensagem acima e os logs locais.
    pause
    exit /b 1
)
exit /b 0
