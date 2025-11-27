Param(
    [string]$NssmPath = "C:\tools\nssm\nssm.exe",
    [string]$ServiceName = "CncTelemetryService",
    [string]$ProjectPath = "C:\cnc-telemetry-main"
)

$ErrorActionPreference = "Stop"

Write-Host "=== CNC TELEMETRY - INSTALAÇÃO DE SERVIÇO VIA NSSM ==="

if (-not (Test-Path $NssmPath)) {
    Write-Host "[ERRO] NSSM não encontrado em: $NssmPath"
    Write-Host "Baixe e extraia o NSSM e ajuste o parâmetro -NssmPath."
    exit 1
}

if (-not (Test-Path $ProjectPath)) {
    Write-Host "[ERRO] Caminho do projeto não encontrado: $ProjectPath"
    exit 1
}

$pythonExe = Join-Path $ProjectPath ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERRO] Python do venv não encontrado em: $pythonExe"
    Write-Host "Crie o venv e instale as dependências antes de instalar o serviço."
    exit 1
}

Write-Host "Parando/removendo serviço existente (se houver)..."
try { & $NssmPath stop $ServiceName | Out-Null } catch { }
try { & $NssmPath remove $ServiceName confirm | Out-Null } catch { }

Write-Host "Configurando serviço $ServiceName usando NSSM..."
& $NssmPath install $ServiceName $pythonExe "-m" "backend.server_entry"
& $NssmPath set $ServiceName AppDirectory $ProjectPath
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName DisplayName "CNC Telemetry Backend"
& $NssmPath set $ServiceName Description "Backend FastAPI do CNC Telemetry"

Write-Host "[OK] Serviço $ServiceName configurado."
Write-Host "Use 'nssm start $ServiceName' ou o services.msc para iniciar."
