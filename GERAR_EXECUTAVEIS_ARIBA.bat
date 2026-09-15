@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo COMPILADOR - MONITOR ARIBA x SAP
echo ============================================================
echo.
echo Esta rotina gera:
echo   dist\BrasmoAribaMonitor.exe
echo   dist\BrasmoAribaMonitorSilent.exe
echo.

if not exist "main.py" (
    echo ERRO: main.py nao foi encontrado nesta pasta.
    echo Coloque este BAT na raiz do projeto, ao lado de main.py.
    echo.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado no PATH.
    echo Execute este BAT em um PC onde o Python esteja instalado.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 goto erro
)

call ".venv\Scripts\activate.bat"

echo.
echo Atualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 goto erro

echo.
echo Instalando dependencias...
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    pip install requests python-dotenv python-dateutil winotify
)
if errorlevel 1 goto erro

echo.
echo Instalando PyInstaller...
pip install pyinstaller
if errorlevel 1 goto erro

echo.
echo Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "BrasmoAribaMonitor.spec" del /q "BrasmoAribaMonitor.spec"
if exist "BrasmoAribaMonitorSilent.spec" del /q "BrasmoAribaMonitorSilent.spec"

echo.
echo ============================================================
echo GERANDO EXECUTAVEL MANUAL
echo ============================================================
pyinstaller --noconfirm --clean --onefile --name BrasmoAribaMonitor --hidden-import winotify --hidden-import dotenv --hidden-import dateutil main.py
if errorlevel 1 goto erro

echo.
echo ============================================================
echo GERANDO EXECUTAVEL SILENCIOSO
echo ============================================================
pyinstaller --noconfirm --clean --onefile --noconsole --name BrasmoAribaMonitorSilent --hidden-import winotify --hidden-import dotenv --hidden-import dateutil main.py
if errorlevel 1 goto erro

echo.
echo ============================================================
echo COMPILACAO CONCLUIDA
echo ============================================================
echo.
echo Arquivos gerados:
echo   %CD%\dist\BrasmoAribaMonitor.exe
echo   %CD%\dist\BrasmoAribaMonitorSilent.exe
echo.
echo Leve somente estes dois EXEs para o outro PC e substitua os antigos.
echo Nao substitua o .env nem data\monitor.db.
echo.
pause
exit /b 0

:erro
echo.
echo ============================================================
echo ERRO NA COMPILACAO
echo ============================================================
echo Veja a mensagem acima e envie uma foto ou copia do erro.
echo.
pause
exit /b 1
