@echo off
REM start_telemetry.bat - Start rápido CNC Telemetry para operador
REM Uso: start_telemetry.bat

echo === CNC Telemetry - Iniciando Sistema ===
echo.

REM Verificar se está no diretório correto
if not exist "backend\main.py" (
    echo ERRO: Execute este script da pasta raiz do projeto
    echo Onde devem existir as pastas 'backend' e 'frontend'
    pause
    exit /b 1
)

REM Verificar virtualenv
if not exist ".venv\Scripts\python.exe" (
    echo ERRO: Virtualenv nao encontrado
    echo Execute primeiro: install_cnc_telemetry.ps1
    pause
    exit /b 1
)

REM Iniciar backend
echo Iniciando backend...
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
if %ERRORLEVEL% neq 0 (
    echo ERRO: Falha ao iniciar backend
    pause
    exit /b 1
)

echo.
echo Backend iniciado! Acesse http://localhost:8001/healthz
echo Pressione CTRL+C para parar
pause
