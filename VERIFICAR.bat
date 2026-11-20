@echo off
rem O verificador apresenta estados locais sem iniciar nem encerrar serviços.
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verificar_ambiente.ps1"
if errorlevel 1 (
    echo.
    echo A verificacao encontrou componentes pendentes.
    pause
    exit /b 1
)
pause
exit /b 0
