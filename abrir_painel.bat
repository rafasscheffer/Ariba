@echo off
cd /d "%~dp0"
if not exist reports\painel.html (
    echo Painel ainda nao existe.
    echo Execute validar_90_dias.bat ou executar_monitor.bat.
    pause
    exit /b 1
)
start "" "%~dp0reports\painel.html"
