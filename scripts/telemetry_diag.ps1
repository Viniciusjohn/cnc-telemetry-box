<#
    telemetry_diag.ps1 - Diagnóstico Completo CNC Telemetry Windows
    Executa verificação completa de 1 minuto para suporte remoto
    Uso: .\scripts\telemetry_diag.ps1 [-Detailed]
#>

param(
    [switch]$Detailed = $false,
    [string]$InstallDir = "C:\cnc-telemetry-main",
    [int]$ApiPort = 8001,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
Write-Host "=== CNC Telemetry Diagnóstico v1.0 ===" -ForegroundColor Cyan
Write-Host "Iniciado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Função helper para seções
function Write-Section {
    param([string]$Title)
    Write-Host "`n--- $Title ---" -ForegroundColor Yellow
}

# Função helper para status OK/FAIL
function Write-Status {
    param([string]$Item, [bool]$Success, [string]$Details = "")
    $status = if ($Success) { "✓ OK" } else { "✗ FAIL" }
    $color = if ($Success) { "Green" } else { "Red" }
    Write-Host "$($Item.PadRight(30)): $status" -ForegroundColor $color
    if ($Details) { Write-Host "    $Details" -ForegroundColor Gray }
}

# 1. INFRAESTURA - Sistema e Pré-requisitos
Write-Section "INFRAESTURA"

# Sistema operacional
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osVersion = "$($osInfo.Caption) $($osInfo.Version)"
Write-Host "Sistema: $osVersion"

# Python
try {
    $pythonVersion = & python --version 2>&1
    Write-Status "Python" $true $pythonVersion
} catch {
    Write-Status "Python" $false "Não encontrado no PATH"
}

# Node/NPM
try {
    $nodeVersion = & node --version 2>&1
    Write-Status "Node.js" $true $nodeVersion
} catch {
    Write-Status "Node.js" $false "Não encontrado no PATH"
}

try {
    $npmVersion = & npm --version 2>&1
    Write-Status "NPM" $true $npmVersion
} catch {
    Write-Status "NPM" $false "Não encontrado no PATH"
}

# NSSM
$nssmPath = "C:\nssm\nssm.exe"
$nssmExists = Test-Path $nssmPath
Write-Status "NSSM" $nssmExists $(if ($nssmExists) { $nssmPath } else { "Não encontrado em C:\nssm\" })

# 2. INSTALAÇÃO - Estrutura de arquivos
Write-Section "INSTALAÇÃO"

$installExists = Test-Path $InstallDir
Write-Status "Diretório instalação" $installExists $InstallDir

if ($installExists) {
    Set-Location $InstallDir
    
    $backendDir = Join-Path $InstallDir "backend"
    $frontendDir = Join-Path $InstallDir "frontend"
    $venvPath = Join-Path $InstallDir ".venv"
    
    Write-Status "Backend" (Test-Path $backendDir) $backendDir
    Write-Status "Frontend" (Test-Path $frontendDir) $frontendDir
    Write-Status "Virtualenv" (Test-Path $venvPath) $venvPath
    
    # Requirements
    $requirementsPath = Join-Path $backendDir "requirements.txt"
    Write-Status "Requirements.txt" (Test-Path $requirementsPath) $requirementsPath
}

# 3. SERVIÇOS - Status do serviço Windows
Write-Section "SERVIÇOS WINDOWS"

$serviceName = "CncTelemetryService"
try {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service) {
        $serviceStatus = $service.Status
        $serviceStartType = $service.StartType
        Write-Status "Serviço Telemetry" ($serviceStatus -eq "Running") "Status: $serviceStatus | Start: $serviceStartType"
        
        if ($Detailed) {
            Write-Host "    Detalhes: $($service.DisplayName) - $($service.Description)" -ForegroundColor Gray
        }
    } else {
        Write-Status "Serviço Telemetry" $false "Não encontrado"
    }
} catch {
    Write-Status "Serviço Telemetry" $false "Erro ao consultar"
}

# 4. REDE - Portas e conectividade
Write-Section "REDE E CONECTIVIDADE"

# Verificar portas em uso
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

$apiPortOpen = Test-Port $ApiPort
Write-Status "Porta API $ApiPort" $apiPortOpen

if ($apiPortOpen) {
    # Testar health endpoint
    try {
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:$ApiPort/healthz" -UseBasicParsing -TimeoutSec 5
        Write-Status "Healthz API" ($healthResponse.StatusCode -eq 200) "HTTP $($healthResponse.StatusCode)"
        
        if ($Detailed -and $healthResponse.Content) {
            try {
                $healthJson = $healthResponse.Content | ConvertFrom-Json
                Write-Host "    Backend: $($healthJson.status)" -ForegroundColor Gray
            } catch {
                Write-Host "    Response: $($healthResponse.Content.Substring(0, [Math]::Min(100, $healthResponse.Content.Length)))" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Status "Healthz API" $false "Timeout ou erro"
    }
} else {
    Write-Status "Healthz API" $false "Porta fechada"
}

# Frontend (se rodando localmente)
$frontendPortOpen = Test-Port $FrontendPort
Write-Status "Porta Frontend $FrontendPort" $frontendPortOpen

# 5. BANCO DE DADOS - Status e arquivos
Write-Section "BANCO DE DADOS"

if ($installExists) {
    $backendDir = Join-Path $InstallDir "backend"
    Set-Location $backendDir
    
    # Verificar .env.beta
    $envFile = ".env.beta"
    $envExists = Test-Path $envFile
    Write-Status "Arquivo .env.beta" $envExists
    
    if ($envExists) {
        $envContent = Get-Content $envFile
        $dbUrl = ($envContent | Where-Object { $_ -match "DATABASE_URL" }) -split "=" | Select-Object -Last 1
        
        if ($dbUrl -match "sqlite") {
            $dbPath = $dbUrl -replace "sqlite:///", ""
            $dbExists = Test-Path $dbPath
            Write-Status "Database SQLite" $dbExists $dbPath
            
            if ($dbExists) {
                $dbSize = [Math]::Round((Get-Item $dbPath).Length / 1MB, 2)
                Write-Host "    Tamanho: $dbSize MB" -ForegroundColor Gray
            }
        } else {
            Write-Status "Database URL" $true $dbUrl
        }
    }
}

# 6. LOGS - Configuração e arquivos
Write-Section "LOGS E DIAGNÓSTICO"

if ($installExists) {
    $logDir = Join-Path $env:PROGRAMDATA "CNC-Telemetry\logs"
    $logExists = Test-Path $logDir
    Write-Status "Diretório logs" $logExists $logDir
    
    if ($logExists) {
        $logFiles = Get-ChildItem $logDir -Filter "*.log" -ErrorAction SilentlyContinue
        Write-Host "    Arquivos de log: $($logFiles.Count)" -ForegroundColor Gray
        
        if ($Detailed -and $logFiles.Count -gt 0) {
            foreach ($file in $logFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 3) {
                $size = [Math]::Round($file.Length / 1KB, 2)
                Write-Host "      $($file.Name) - $size KB - $($file.LastWriteTime)" -ForegroundColor Gray
            }
        }
    }
}

# 7. RECURSOS DO SISTEMA
Write-Section "RECURSOS DO SISTEMA"

$cpu = Get-CimInstance -ClassName Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object Average
$memory = Get-CimInstance -ClassName Win32_OperatingSystem
$memFree = [Math]::Round($memory.FreePhysicalMemory / 1MB, 2)
$memTotal = [Math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
$memUsage = [Math]::Round((($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize) * 100, 2)

Write-Host "CPU Usage: $($cpu.Average)%"
Write-Host "Memory: $memFree GB free of $memTotal GB ($memUsage% used)"

# Verificar disco
$installDrive = (Get-Item $InstallDir).Root
$disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$installDrive'"
$diskFree = [Math]::Round($disk.FreeSpace / 1GB, 2)
$diskTotal = [Math]::Round($disk.Size / 1GB, 2)
$diskUsage = [Math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 2)

Write-Host "Disco $installDrive`: $diskFree GB free of $diskTotal GB ($diskUsage% used)"

# 8. RESUMO E RECOMENDAÇÕES
Write-Section "RESUMO"

$issues = @()

if (-not $nssmExists) { $issues += "NSSM não encontrado" }
if (-not $apiPortOpen) { $issues += "API não respondendo na porta $ApiPort" }
if ($memUsage -gt 85) { $issues += "Uso de memória elevado ($memUsage%)" }
if ($diskUsage -gt 90) { $issues += "Disco quase cheio ($diskUsage%)" }

if ($issues.Count -eq 0) {
    Write-Host "✓ Sistema operando normalmente" -ForegroundColor Green
} else {
    Write-Host "✗ Problemas detectados:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
}

Write-Host "`nDiagnóstico concluído: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Exportar resultado para arquivo se detailed
if ($Detailed) {
    $reportPath = Join-Path $env:TEMP "telemetry-diag-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
    Write-Host "`nRelatório detalhado salvo em: $reportPath" -ForegroundColor Cyan
}

Write-Host "`nPara suporte, envie este resultado junto com:" -ForegroundColor Cyan
Write-Host "1. Versão do Windows e build" -ForegroundColor Gray
Write-Host "2. Logs de: $logDir" -ForegroundColor Gray
Write-Host "3. Print do erro (se aplicável)" -ForegroundColor Gray
