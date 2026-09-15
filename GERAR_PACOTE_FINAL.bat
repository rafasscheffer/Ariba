@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo GERAR PACOTE FINAL - MONITOR ARIBA x SAP
echo ============================================================
echo.

if not exist "main.py" (
    echo ERRO: main.py nao encontrado.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERRO: .env nao encontrado nesta pasta.
    pause
    exit /b 1
)

if not exist "data\monitor.db" (
    echo ERRO: data\monitor.db nao encontrado.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto erro
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto erro
pip install -r requirements.txt
if errorlevel 1 goto erro
pip install pyinstaller
if errorlevel 1 goto erro

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist BrasmoAribaMonitor.spec del /q BrasmoAribaMonitor.spec
if exist BrasmoAribaMonitorSilent.spec del /q BrasmoAribaMonitorSilent.spec

pyinstaller --noconfirm --clean --onefile --name BrasmoAribaMonitor --hidden-import winotify --hidden-import dotenv --hidden-import dateutil main.py
if errorlevel 1 goto erro

pyinstaller --noconfirm --clean --onefile --noconsole --name BrasmoAribaMonitorSilent --hidden-import winotify --hidden-import dotenv --hidden-import dateutil main.py
if errorlevel 1 goto erro

echo.
echo Testando o EXE manual contra o .env desta pasta...
"dist\BrasmoAribaMonitor.exe" test
if errorlevel 1 (
    echo.
    echo ERRO: o EXE foi gerado, mas o teste de conexao falhou.
    echo Nao copie para o outro PC antes de corrigir.
    pause
    exit /b 1
)

if exist PACOTE_PENDRIVE rmdir /s /q PACOTE_PENDRIVE
mkdir PACOTE_PENDRIVE
mkdir PACOTE_PENDRIVE\data
mkdir PACOTE_PENDRIVE\reports
mkdir PACOTE_PENDRIVE\logs

copy /y "dist\BrasmoAribaMonitor.exe" "PACOTE_PENDRIVE\" >nul
copy /y "dist\BrasmoAribaMonitorSilent.exe" "PACOTE_PENDRIVE\" >nul
copy /y ".env" "PACOTE_PENDRIVE\" >nul
copy /y "data\monitor.db" "PACOTE_PENDRIVE\data\" >nul
if exist "reports\*" xcopy /e /i /y "reports\*" "PACOTE_PENDRIVE\reports\" >nul

copy /y "01 - Abrir Painel.bat" "PACOTE_PENDRIVE\" >nul
copy /y "02 - Executar Monitor Agora.bat" "PACOTE_PENDRIVE\" >nul
copy /y "03 - Gerar e Abrir Relatorios.bat" "PACOTE_PENDRIVE\" >nul
copy /y "04 - Testar Conexoes.bat" "PACOTE_PENDRIVE\" >nul
copy /y "instalar_tarefas.ps1" "PACOTE_PENDRIVE\" >nul
copy /y "instalar_tarefas.bat" "PACOTE_PENDRIVE\" >nul
copy /y "remover_tarefas.ps1" "PACOTE_PENDRIVE\" >nul
copy /y "remover_tarefas.bat" "PACOTE_PENDRIVE\" >nul


echo.
echo ============================================================
echo PACOTE PRONTO
 echo ============================================================
echo.
echo Pasta para levar no pendrive:
echo   %CD%\PACOTE_PENDRIVE
echo.
echo Antes de sair deste PC, entre nessa pasta e execute:
echo   04 - Testar Conexoes.bat
echo.
pause
exit /b 0

:erro
echo.
echo ERRO DURANTE A COMPILACAO.
echo Veja a mensagem acima.
pause
exit /b 1
