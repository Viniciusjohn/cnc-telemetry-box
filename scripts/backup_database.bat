@echo off
REM backup_database.bat - Backup automatico do banco SQLite
REM Uso: backup_database.bat [destino]

setlocal enabledelayedexpansion

echo === CNC Telemetry - Backup Database ===
echo.

REM Configurar paths
set INSTALL_DIR=C:\cnc-telemetry-main
set BACKEND_DIR=%INSTALL_DIR%\backend
set ENV_FILE=%BACKEND_DIR%\.env.beta

REM Verificar se está no diretório certo
if not exist "%ENV_FILE%" (
    echo ERRO: Arquivo .env.beta nao encontrado em %BACKEND_DIR%
    pause
    exit /b 1
)

REM Ler database URL do .env
set DB_URL=
for /f "tokens=2 delims==" %%a in ('findstr "DATABASE_URL" "%ENV_FILE%"') do set DB_URL=%%a

if "%DB_URL%"=="" (
    echo ERRO: DATABASE_URL nao encontrado em %ENV_FILE%
    pause
    exit /b 1
)

REM Extrair path do arquivo SQLite
set DB_FILE=%DB_URL:sqlite:///%

if not exist "%DB_FILE%" (
    echo ERRO: Arquivo de banco nao encontrado: %DB_FILE%
    pause
    exit /b 1
)

REM Configurar destino do backup
if "%1"=="" (
    set BACKUP_DIR=%INSTALL_DIR%\backups
) else (
    set BACKUP_DIR=%1
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Gerar nome do arquivo com timestamp
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATE=%%c%%a%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIME=%%a%%b
set TIME=%TIME: =0%
set BACKUP_FILE=%BACKUP_DIR%\telemetry_backup_%DATE%_%TIME%.db

REM Executar backup
echo Fazendo backup de %DB_FILE% para %BACKUP_FILE%...
copy "%DB_FILE%" "%BACKUP_FILE%" >nul

if %ERRORLEVEL% equ 0 (
    echo %GREEN%SUCESSO%RESET% - Backup criado
    echo Arquivo: %BACKUP_FILE%
    
    REM Verificar tamanho
    for %%F in ("%BACKUP_FILE%") do set SIZE=%%~zF
    set /a SIZE_MB=%SIZE%/1048576
    echo Tamanho: %SIZE_MB% MB
    
    REM Manter apenas os 7 backups mais recentes
    echo Limpando backups antigos...
    for /f "skip=7 delims=" %%F in ('dir "%BACKUP_DIR%\telemetry_backup_*.db" /b /o-d 2^>nul') do del "%BACKUP_DIR%\%%F"
    
) else (
    echo %RED%ERRO%RESET% - Falha no backup
    pause
    exit /b 1
)

echo.
echo Backup concluido!
pause
