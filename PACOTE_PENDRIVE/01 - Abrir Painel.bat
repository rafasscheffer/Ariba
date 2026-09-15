@echo off
cd /d "%~dp0"
if not exist "reports\painel.html" (
    echo Painel ainda nao existe. Execute o monitor primeiro.
    pause
    exit /b 1
)
start "" "%~dp0reports\painel.html"
