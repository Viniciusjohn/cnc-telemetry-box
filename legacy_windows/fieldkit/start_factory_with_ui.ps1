# CNC Telemetry FieldKit — start_factory_with_ui.ps1
# Sobe backend + adapter (via start_factory_1click.ps1) e abre o frontend DEV (npm run dev).

param(
    [string]$AgentUrl,
    [string]$MachineId = "M80-FABRICA-01"
)

$ErrorActionPreference = "Stop"

# Raiz do FieldKit (onde este script está)
$KitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $KitRoot) {
    $KitRoot = "C:\cnc-telemetry-fieldkit"
}

$StartBackend = Join-Path $KitRoot "start_factory_1click.ps1"

if (-not (Test-Path $StartBackend)) {
    Write-Error "Nao encontrei $StartBackend. Confirme que o FieldKit (start_factory_1click.ps1) esta na mesma pasta."
    exit 1
}

Write-Host "=== [1/2] Subindo backend + adapter (FieldKit) ===" -ForegroundColor Cyan
& $StartBackend -AgentUrl $AgentUrl -MachineId $MachineId

Write-Host "" 
Write-Host "=== [2/2] Abrindo frontend DEV (npm run dev) ===" -ForegroundColor Cyan

$FrontendDir = "C:\cnc-telemetry-main\frontend"

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Error "Frontend nao encontrado em $FrontendDir (package.json ausente)."
    exit 1
}

# Comando que a nova janela de PowerShell vai rodar
$frontendCmd = @"
`$env:VITE_API_BASE   = "http://127.0.0.1:8001";
`$env:VITE_MACHINE_ID = "$MachineId";
Set-Location "$FrontendDir";
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "" 
Write-Host "FieldKit + UI DEV iniciados." -ForegroundColor Green
Write-Host " - Backend/adapter: ver janela/logs do FieldKit"
Write-Host " - UI: abrir http://localhost:5173 no navegador"
