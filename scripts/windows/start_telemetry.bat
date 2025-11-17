@echo off
REM === CNC Telemetry - start_telemetry.bat (Windows) ===
REM Executa o backend FastAPI em modo desenvolvimento

REM Ir para a raiz do projeto
cd /d C:\cnc-telemetry-main

REM Ativar o ambiente virtual, se existir
if exist .venv (
    call .venv\Scripts\activate.bat
) else (
    echo [ERRO] Ambiente virtual .venv nao encontrado em C:\cnc-telemetry-main
    echo Crie o venv com:
    echo     python -m venv .venv
    echo Depois instale as dependencias com:
    echo     .venv\Scripts\activate.bat
    echo     pip install -r backend\requirements.txt
    pause
    exit /b 1
)

REM Iniciar o servidor FastAPI
echo Iniciando CNC Telemetry (backend)...
python -m backend.server_entry

REM Mantem a janela aberta se algo der errado
if %errorlevel% neq 0 (
    echo [ERRO] O servidor encerrou com codigo %errorlevel%.
    pause
)
