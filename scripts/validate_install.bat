@echo off
REM validate_install.bat - Validacao completa pos-instalacao
REM Gera relatorio verde/vermelho para screenshot do instalador
REM Uso: validate_install.bat

setlocal enabledelayedexpansion

echo === CNC Telemetry - Validacao de Instalacao ===
echo.

REM Cores
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set BLUE=[94m
set RESET=[0m

REM Contador de testes
set TOTAL_TESTS=0
set PASSED_TESTS=0

REM Funcao para exibir resultado do teste
:TEST_RESULT
set /a TOTAL_TESTS+=1
if "%1"=="PASS" (
    set /a PASSED_TESTS+=1
    echo %GREEN%[PASS]%RESET% %2
) else (
    echo %RED%[FAIL]%RESET% %2
    if not "%3"=="" echo    Detalhe: %3
)
goto :eof

REM Iniciar relatorio
echo Relatorio de Validacao - CNC Telemetry
echo Data: %date% %time%
echo ========================================
echo.

REM Teste 1: Estrutura de diretorios
echo %BLUE%1. Verificando estrutura de instalacao...%RESET%

call :TEST_RESULT "PASS" "Diretorio raiz existe"
if exist "backend\main.py" (
    call :TEST_RESULT "PASS" "Backend encontrado"
) else (
    call :TEST_RESULT "FAIL" "Backend nao encontrado"
)

if exist "frontend\package.json" (
    call :TEST_RESULT "PASS" "Frontend encontrado"
) else (
    call :TEST_RESULT "FAIL" "Frontend nao encontrado"
)

if exist ".venv\Scripts\python.exe" (
    call :TEST_RESULT "PASS" "Virtualenv configurado"
) else (
    call :TEST_RESULT "FAIL" "Virtualenv nao encontrado"
)

echo.

REM Teste 2: Dependencias Python
echo %BLUE%2. Verificando dependencias Python...%RESET%

cd backend
..\.venv\Scripts\python.exe -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :TEST_RESULT "PASS" "Dependencias Python OK"
) else (
    call :TEST_RESULT "FAIL" "Dependencias Python faltando"
)

REM Teste 3: Configuracao
echo.
echo %BLUE%3. Verificando configuracao...%RESET%

if exist ".env.beta" (
    call :TEST_RESULT "PASS" "Arquivo .env.beta existe"
    
    REM Verificar DATABASE_URL
    findstr "DATABASE_URL" ".env.beta" >nul
    if %ERRORLEVEL% equ 0 (
        call :TEST_RESULT "PASS" "DATABASE_URL configurado"
    ) else (
        call :TEST_RESULT "FAIL" "DATABASE_URL nao configurado"
    )
) else (
    call :TEST_RESULT "FAIL" "Arquivo .env.beta nao existe"
)

REM Teste 4: Banco de dados
echo.
echo %BLUE%4. Verificando banco de dados...%RESET%

REM Extrair DB path
for /f "tokens=2 delims==" %%a in ('findstr "DATABASE_URL" ".env.beta"') do set DB_URL=%%a
set DB_FILE=%DB_URL:sqlite:///%

if exist "%DB_FILE%" (
    call :TEST_RESULT "PASS" "Arquivo de banco existe"
    
    REM Testar conexao
    ..\.venv\Scripts\python.exe -c "
import sqlite3
try:
    conn = sqlite3.connect(r'%DB_FILE%')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    tables = cursor.fetchall()
    print(f'{len(tables)} tabelas encontradas')
    conn.close()
except Exception as e:
    print(f'Erro: {e}')
    exit(1)
" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        call :TEST_RESULT "PASS" "Banco acessivel"
    ) else (
        call :TEST_RESULT "FAIL" "Banco nao acessivel"
    )
) else (
    call :TEST_RESULT "FAIL" "Arquivo de banco nao existe"
)

REM Teste 5: Servico Windows
echo.
echo %BLUE%5. Verificando servico Windows...%RESET%

sc query CncTelemetryService | findstr "RUNNING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :TEST_RESULT "PASS" "Servico rodando"
) else (
    call :TEST_RESULT "FAIL" "Servico nao esta rodando"
)

REM Teste 6: API Backend
echo.
echo %BLUE%6. Verificando API Backend...%RESET%

REM Aguardar API subir
echo Aguardando API iniciar...
timeout /t 10 /nobreak >nul

REM Testar health endpoint
curl -s http://localhost:8001/healthz >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :TEST_RESULT "PASS" "Health endpoint responde"
    
    REM Testar resposta JSON
    curl -s http://localhost:8001/healthz | findstr "status" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        call :TEST_RESULT "PASS" "Health endpoint retorna JSON"
    ) else (
        call :TEST_RESULT "FAIL" "Health endpoint JSON invalido"
    )
) else (
    call :TEST_RESULT "FAIL" "Health endpoint nao responde"
)

REM Teste 7: Frontend build
echo.
echo %BLUE%7. Verificando Frontend...%RESET%

cd ..\frontend
if exist "dist\index.html" (
    call :TEST_RESULT "PASS" "Frontend buildado"
    
    REM Verificar tamanho do build
    for %%F in ("dist\index.html") do set SIZE=%%~zF
    if %SIZE% gtr 1000 (
        call :TEST_RESULT "PASS" "Frontend tamanho adequado"
    ) else (
        call :TEST_RESULT "FAIL" "Frontend build muito pequeno"
    )
) else (
    call :TEST_RESULT "FAIL" "Frontend nao buildado"
)

REM Teste 8: Rede e Firewall
echo.
echo %BLUE%8. Verificando rede...%RESET%

netstat -ano | findstr :8001 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :TEST_RESULT "PASS" "Porta API aberta"
) else (
    call :TEST_RESULT "FAIL" "Porta API fechada"
)

REM Testar acesso local
curl -s -I http://localhost:8001/healthz | findstr "200 OK" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    call :TEST_RESULT "PASS" "Acesso local funcionando"
) else (
    call :TEST_RESULT "FAIL" "Acesso local com problemas"
)

cd ..

REM Resumo final
echo.
echo ========================================
echo %BLUE%RESUMO DA VALIDACAO%RESET%
echo ========================================
echo Testes executados: %TOTAL_TESTS%
echo Testes passados: %PASSED_TESTS%

set /a FAIL_COUNT=%TOTAL_TESTS%-%PASSED_TESTS%
echo Testes falhados: %FAIL_COUNT%

echo.
if %FAIL_COUNT% equ 0 (
    echo %GREEN%✓ INSTALACAO 100%% BEM-SUCEDIDA%RESET%
    echo Sistema pronto para uso em producao!
    echo.
    echo URLs de acesso:
    echo   API: http://localhost:8001
    echo   Health: http://localhost:8001/healthz
    echo   Frontend: http://localhost:3000 (se servidor iniciado)
) else (
    echo %RED%✗ INSTALACO COM PROBLEMAS%RESET%
    echo %FAIL_COUNT% teste(s) falharam - verificar itens acima
    echo.
    echo Comandos uteis para correcao:
    echo   - Reinstalar servico: nssm stop CncTelemetryService ^&^& nssm start CncTelemetryService
    echo   - Verificar logs: type "%PROGRAMDATA%\CNC-Telemetry\logs\telemetry.log"
    echo   - Diagnostico completo: .\scripts\telemetry_diag.ps1
)

echo.
echo Relatorio gerado em: %date% %time%
echo Salve este screenshot para registro da instalacao.

pause
