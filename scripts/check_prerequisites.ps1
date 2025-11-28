<#
    check_prerequisites.ps1 - Verificação de Pré-requisitos CNC Telemetry
    Executa antes da instalação para garantir ambiente adequado
    Uso: .\scripts\check_prerequisites.ps1
#>

param(
    [string]$InstallDir = "C:\cnc-telemetry-main"
)

$ErrorActionPreference = "Stop"
Write-Host "=== CNC Telemetry - Verificação de Pré-requisitos ===" -ForegroundColor Cyan

# Função helper para status
function Write-Status {
    param([string]$Item, [bool]$Success, [string]$Details = "")
    $status = if ($Success) { "[OK]" } else { "[FAIL]" }
    $color = if ($Success) { "Green" } else { "Red" }
    Write-Host "$($Item.PadRight(35)): $status" -ForegroundColor $color
    if ($Details) { Write-Host "    $Details" -ForegroundColor Gray }
    return $Success
}

# Contador de falhas
$failures = 0

Write-Host "`n--- SISTEMA OPERACIONAL ---" -ForegroundColor Yellow

# 1. Versão Windows
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osVersion = "$($osInfo.Caption)"
$osSupported = $osVersion -match "Windows 10|Windows 11|Windows Server"
if (-not (Write-Status "Windows versão" $osSupported $osVersion)) { $failures++ }

# 2. Arquitetura x64
$architecture = $env:PROCESSOR_ARCHITECTURE
if (-not (Write-Status "Arquitetura x64" ($architecture -eq "AMD64") $architecture)) { $failures++ }

# 3. Permissões Administrativas (CRÍTICO)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not (Write-Status "Permissões Administrativas" $isAdmin "CRÍTICO para instalação")) { 
    $failures++
    Write-Host "    SOLUÇÃO: Execute PowerShell como Administrador" -ForegroundColor Yellow
}

Write-Host "`n--- HARDWARE ---" -ForegroundColor Yellow

# 4. RAM mínima (4GB)
$memory = Get-CimInstance -ClassName Win32_OperatingSystem
$ramGB = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
if (-not (Write-Status "RAM mínima 4GB" ($ramGB -ge 4) "$ramGB GB disponíveis")) { $failures++ }

# 5. Disco livre (20GB)
$disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$diskFreeGB = [math]::Round($disk.FreeSpace / 1GB, 2)
if (-not (Write-Status "Disco livre 20GB" ($diskFreeGB -ge 20) "$diskFreeGB GB livres")) { $failures++ }

Write-Host "`n--- REDE ---" -ForegroundColor Yellow

# 6. Conectividade Internet
try {
    $test = Test-NetConnection -ComputerName "google.com" -Port 443 -InformationLevel Quiet
    Write-Status "Conectividade Internet" $test "Para downloads"
} catch {
    if (-not (Write-Status "Conectividade Internet" $false "Não foi possível testar")) { $failures++ }
}

# 7. Porta 8001 disponível
try {
    $port8001 = Test-NetConnection -ComputerName "localhost" -Port 8001 -InformationLevel Quiet
    Write-Status "Porta 8001 disponível" (-not $port8001) "API backend"
} catch {
    Write-Status "Porta 8001 disponível" $true "API backend"
}

# 8. Porta 3000 disponível
try {
    $port3000 = Test-NetConnection -ComputerName "localhost" -Port 3000 -InformationLevel Quiet
    Write-Status "Porta 3000 disponível" (-not $port3000) "Frontend"
} catch {
    Write-Status "Porta 3000 disponível" $true "Frontend"
}

Write-Host "`n--- SOFTWARE NECESSÁRIO ---" -ForegroundColor Yellow

# 9. Python 3.8+
try {
    $pythonVersion = & python --version 2>&1
    $pythonOK = $pythonVersion -match "Python 3\.[8-9]|Python 3\.1[0-9]"
    if (-not (Write-Status "Python 3.8+" $pythonOK $pythonVersion)) { $failures++ }
} catch {
    Write-Status "Python 3.8+" $false "Não encontrado no PATH"
    $failures++
}

# 10. Node.js 16+
try {
    $nodeVersion = & node --version 2>&1
    $nodeOK = $nodeVersion -match "v1[6-9]|v2[0-9]"
    if (-not (Write-Status "Node.js 16+" $nodeOK $nodeVersion)) { $failures++ }
} catch {
    Write-Status "Node.js 16+" $false "Não encontrado no PATH"
    $failures++
}

# 11. NPM
try {
    $npmVersion = & npm --version 2>&1
    Write-Status "NPM" $true $npmVersion
} catch {
    Write-Status "NPM" $false "Não encontrado no PATH"
    $failures++
}

# 12. Git
try {
    $gitVersion = & git --version 2>&1
    Write-Status "Git" $true $gitVersion
} catch {
    Write-Status "Git" $false "Não encontrado no PATH"
    $failures++
}

# 13. NSSM
$nssmPath = "C:\nssm\nssm.exe"
$nssmExists = Test-Path $nssmPath
if (-not (Write-Status "NSSM" $nssmExists $nssmPath)) { 
    $failures++
    Write-Host "    SOLUÇÃO: Instale NSSM em C:\nssm\" -ForegroundColor Yellow
}

Write-Host "`n--- AMBIENTE ---" -ForegroundColor Yellow

# 14. Diretório de instalação disponível
$installExists = Test-Path $InstallDir
if ($installExists) {
    Write-Status "Diretório instalação" $true "Já existe: $InstallDir"
} else {
    # Verificar se podemos criar
    try {
        $parentDir = Split-Path $InstallDir -Parent
        if (Test-Path $parentDir) {
            Write-Status "Diretório instalação" $true "Pode ser criado: $InstallDir"
        } else {
            Write-Status "Diretório instalação" $false "Diretório pai não existe: $parentDir"
            $failures++
        }
    } catch {
        Write-Status "Diretório instalação" $false "Sem permissão para criar: $InstallDir"
        $failures++
    }
}

# 15. Antivírus (aviso)
try {
    $antivirus = Get-CimInstance -Namespace "root\SecurityCenter2" -ClassName AntivirusProduct -ErrorAction SilentlyContinue
    if ($antivirus) {
        Write-Status "Antivírus detectado" $true "$($antivirus.displayName) - pode interferir"
        Write-Host "    RECOMENDAÇÃO: Desabilite temporariamente durante instalação" -ForegroundColor Yellow
    } else {
        Write-Status "Antivírus detectado" $true "Nenhum detectado"
    }
} catch {
    Write-Status "Antivírus detectado" $true "Não foi possível verificar"
}

Write-Host "`n=== RESUMO ===" -ForegroundColor Cyan

if ($failures -eq 0) {
    Write-Host "[OK] Todos os pré-requisitos atendidos!" -ForegroundColor Green
    Write-Host "Você pode prosseguir com a instalação:" -ForegroundColor Green
    Write-Host "    .\install_cnc_telemetry.ps1" -ForegroundColor White
    exit 0
} else {
    Write-Host "[FAIL] $failures pré-requisito(s) não atendido(s)" -ForegroundColor Red
    Write-Host "Resolva os itens acima antes de prosseguir com a instalação." -ForegroundColor Red
    Write-Host "Execute este script novamente após as correções." -ForegroundColor Yellow
    exit 1
}
