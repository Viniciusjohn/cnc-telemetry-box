@echo off
REM === CNC Telemetry - start_telemetry.bat ===
REM Sobe o backend em modo desenvolvimento no Windows

cd /d C:\cnc-telemetry-main

REM Ativar venv
call .venv\Scripts\activate.bat

REM Iniciar o servidor FastAPI (Uvicorn)
python -m backend.server_entry
