@echo off
REM status.bat - Verificação rápida de status CNC Telemetry
REM Uso: status.bat

echo === CNC Telemetry - Status do Sistema ===
echo.

REM Cores para melhor visualização
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set RESET=[0m

REM Verificar serviço Windows
echo Servico Backend:
sc query CncTelemetryService | findstr "RUNNING" >nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%RUNNING%RESET% - Operacional
) else (
    echo %RED%PARADO%RESET% - Necessita atencao
)

REM Verificar porta API
echo.
echo Porta API (8001):
netstat -ano | findstr :8001 >nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%ABERTA%RESET% - Respondendo
) else (
    echo %RED%FECHADA%RESET% - Backend nao rodando
)

REM Testar health endpoint
echo.
echo Health Check:
curl -s http://localhost:8001/healthz >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %GREEN%OK%RESET% - API saudavel
) else (
    echo %RED%FALHA%RESET% - API nao respondendo
)

REM Verificar disco
echo.
echo Espaco em Disco:
for /f "tokens=3" %%a in ('dir c:\ ^| find "bytes free"') do set freebytes=%%a
for /f "tokens=1-3 delims=," %%a in ("%freebytes%") do set freespace=%%a
set freespace=%freespace: =%
echo %freespace% bytes livres

REM Verificar uso de memoria
echo.
echo Uso de Memoria:
for /f "skip=1" %%p in ('wmic os get TotalVisibleMemorySize^,FreePhysicalMemory /format:list ^| find "="') do (
    echo %%p | find "TotalVisibleMemorySize" >nul && set total=%%p
    echo %%p | find "FreePhysicalMemory" >nul && set free=%%p
)
set total=%total:*=%
set free=%free:*=%
set /a usage=(%total%-%free%)*100/%total%
echo %usage%% utilizado

echo.
echo === Resumo ===
if %ERRORLEVEL% equ 0 (
    echo %GREEN%SISTEMA OPERACIONAL%RESET%
) else (
    echo %YELLOW%VERIFICAR PROBLEMAS%RESET%
)

echo.
echo Para diagnosticos detalhados, execute: telemetry_diag.ps1
pause
