@echo off
rem O encerrador delega paradas controladas dos processos pertencentes ao projeto.
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\parar.ps1"
if errorlevel 1 (
    echo.
    echo O encerramento seguro nao foi confirmado.
    pause
    exit /b 1
)
pause
exit /b 0
