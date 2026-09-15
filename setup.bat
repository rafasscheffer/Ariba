@echo off
cd /d "%~dp0"

echo ============================================================
echo CONFIGURANDO MONITOR ARIBA x SAP
echo ============================================================

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env >nul
    echo.
    echo .env criado. Preencha suas credenciais.
) else (
    echo.
    echo .env ja existe e foi preservado.
)

echo.
pause
