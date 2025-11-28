@echo off
REM stop_telemetry.bat - Parada CNC Telemetry
REM Uso: stop_telemetry.bat

echo === CNC Telemetry - Parando Sistema ===
echo.

REM Parar serviço Windows (se existir)
echo Parando servico Windows...
sc stop CncTelemetryService >nul 2>&1

REM Matar processos uvicorn restantes
echo Finalizando processos uvicorn...
taskkill /f /im python.exe /fi "WINDOWTITLE eq uvicorn*" >nul 2>&1
taskkill /f /im uvicorn.exe >nul 2>&1

REM Liberar porta 8001
echo Verificando porta 8001...
netstat -ano | findstr :8001 >nul
if %ERRORLEVEL% equ 0 (
    echo Porta 8001 estava em uso, processo finalizado
) else (
    echo Porta 8001 liberada
)

echo.
echo Sistema CNC Telemetry parado com sucesso!
pause
