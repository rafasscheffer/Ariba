@echo off
cd /d "%~dp0"
if not exist reports (
    echo Pasta reports ainda nao existe.
    pause
    exit /b 1
)
start "" "%~dp0reports"
