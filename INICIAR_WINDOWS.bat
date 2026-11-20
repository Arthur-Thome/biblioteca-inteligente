@echo off
rem O atalho legado encaminha a inicializacao para o script local atual.
call "%~dp0INICIAR.bat"
exit /b %errorlevel%
