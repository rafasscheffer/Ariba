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
    echo ERRO: .env nao encontrado na raiz do projeto.
    pause
    exit /b 1
)

if not exist "data\monitor.db" (
    echo ERRO: data\monitor.db nao encontrado.
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
echo Instalando dependencias...
python -m pip install --upgrade pip
if errorlevel 1 goto erro

if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    pip install requests python-dotenv python-dateutil winotify pyinstaller
)
if errorlevel 1 goto erro

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
echo COMPILANDO EXECUTAVEL MANUAL
echo ============================================================
pyinstaller --noconfirm --clean --onefile ^
  --name BrasmoAribaMonitor ^
  --hidden-import winotify ^
  --hidden-import dotenv ^
  --hidden-import dateutil ^
  main.py

if errorlevel 1 goto erro

echo.
echo ============================================================
echo COMPILANDO EXECUTAVEL SILENCIOSO
echo ============================================================
pyinstaller --noconfirm --clean --onefile --noconsole ^
  --name BrasmoAribaMonitorSilent ^
  --hidden-import winotify ^
  --hidden-import dotenv ^
  --hidden-import dateutil ^
  main.py

if errorlevel 1 goto erro

echo.
echo Copiando .env para a pasta dist para o teste...
copy /Y ".env" "dist\.env" >nul

echo.
echo ============================================================
echo TESTANDO O EXE MANUAL
echo ============================================================
pushd "dist"
BrasmoAribaMonitor.exe test
set TEST_RESULT=%ERRORLEVEL%
popd

if not "%TEST_RESULT%"=="0" (
    echo.
    echo ERRO: o EXE foi gerado, mas o teste de conexao falhou.
    echo O .env ja foi copiado para dist, entao agora o erro e real.
    echo Nao copie para o outro PC antes de corrigir.
    echo.
    pause
    exit /b 1
)

echo.
echo Teste concluido com sucesso.
echo.

if exist "PACOTE_PENDRIVE" rmdir /s /q "PACOTE_PENDRIVE"

mkdir "PACOTE_PENDRIVE"
mkdir "PACOTE_PENDRIVE\data"
mkdir "PACOTE_PENDRIVE\reports"
mkdir "PACOTE_PENDRIVE\logs"

copy /Y "dist\BrasmoAribaMonitor.exe" "PACOTE_PENDRIVE\" >nul
copy /Y "dist\BrasmoAribaMonitorSilent.exe" "PACOTE_PENDRIVE\" >nul
copy /Y ".env" "PACOTE_PENDRIVE\" >nul
copy /Y "data\monitor.db" "PACOTE_PENDRIVE\data\" >nul

if exist "reports\*" (
    xcopy /E /I /Y "reports\*" "PACOTE_PENDRIVE\reports\" >nul
)

if exist "logs\monitor.log" (
    copy /Y "logs\monitor.log" "PACOTE_PENDRIVE\logs\" >nul
)

if exist "01 - Abrir Painel.bat" (
    copy /Y "01 - Abrir Painel.bat" "PACOTE_PENDRIVE\" >nul
)

if exist "02 - Executar Monitor Agora.bat" (
    copy /Y "02 - Executar Monitor Agora.bat" "PACOTE_PENDRIVE\" >nul
)

if exist "03 - Gerar e Abrir Relatorios.bat" (
    copy /Y "03 - Gerar e Abrir Relatorios.bat" "PACOTE_PENDRIVE\" >nul
)

if exist "04 - Testar Conexoes.bat" (
    copy /Y "04 - Testar Conexoes.bat" "PACOTE_PENDRIVE\" >nul
)

if exist "instalar_tarefas.ps1" (
    copy /Y "instalar_tarefas.ps1" "PACOTE_PENDRIVE\" >nul
)

if exist "instalar_tarefas.bat" (
    copy /Y "instalar_tarefas.bat" "PACOTE_PENDRIVE\" >nul
)

if exist "INSTALAR_NO_PC.bat" (
    copy /Y "INSTALAR_NO_PC.bat" "PACOTE_PENDRIVE\" >nul
)

echo.
echo ============================================================
echo PACOTE PRONTO
echo ============================================================
echo.
echo Pasta:
echo   %CD%\PACOTE_PENDRIVE
echo.
echo O teste do EXE passou.
echo Agora copie a pasta PACOTE_PENDRIVE para o pendrive.
echo.
pause
exit /b 0

:erro
echo.
echo ============================================================
echo ERRO NA COMPILACAO
echo ============================================================
echo Veja a mensagem acima.
echo.
pause
exit /b 1
