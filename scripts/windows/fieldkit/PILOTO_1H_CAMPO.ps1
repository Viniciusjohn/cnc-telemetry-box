<#
PILOTO_1H_CAMPO.ps1
Roteiro de campo para validar Agent MTConnect + pipeline cnc-telemetry.
Parte A: validar Agent (ping/porta/probe/current/sample).
Parte B: registrar snapshots de /healthz e /status durante o piloto.
#>

param(
    [string]$AgentUrl,
    [string]$MachineId
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

$logsDir = Join-Path $scriptRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

if (-not $AgentUrl) {
    $AgentUrl = Read-Host "AGENT_URL do Agent MTConnect (ex: http://192.168.3.14:5000)"
}
if (-not $MachineId) {
    $MachineId = Read-Host "MACHINE_ID real (ex: M80-FABRICA-01)"
}

$uri = $null
try {
    $uri = [Uri]$AgentUrl
} catch {
    Write-Error "AGENT_URL invalido: $AgentUrl"
    exit 1
}

$agentHost = $uri.Host
$port = $uri.Port

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$agentLog = Join-Path $logsDir ("agent_check_{0}.log" -f $timestamp)
$pilotLog = Join-Path $logsDir ("piloto_{0}.log" -f $timestamp)

"=== PILOTO 1H CAMPO - PARTE A (Agent) ===" | Out-File -FilePath $agentLog -Encoding UTF8
"AgentUrl=$AgentUrl" | Out-File -FilePath $agentLog -Append
"MachineId=$MachineId" | Out-File -FilePath $agentLog -Append

# 1) Ping
"`n[1] Ping $agentHost" | Out-File -FilePath $agentLog -Append
try {
    Test-Connection -ComputerName $agentHost -Count 4 -ErrorAction Stop | Out-String | Out-File -FilePath $agentLog -Append
} catch {
    "Ping falhou: $_" | Out-File -FilePath $agentLog -Append
}

# 2) Porta TCP
("`n[2] Teste de porta TCP {0}:{1}" -f $agentHost, $port) | Out-File -FilePath $agentLog -Append
try {
    Test-NetConnection -ComputerName $agentHost -Port $port -WarningAction SilentlyContinue | Out-String | Out-File -FilePath $agentLog -Append
} catch {
    "Teste de porta falhou: $_" | Out-File -FilePath $agentLog -Append
}

# 3) Endpoints MTConnect
$paths = @("/probe", "/current", "/sample?count=1")
foreach ($path in $paths) {
    $url = "{0}{1}" -f $AgentUrl.TrimEnd('/'), $path
    "`n[3] GET $url" | Out-File -FilePath $agentLog -Append
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
        "HTTP $($resp.StatusCode)" | Out-File -FilePath $agentLog -Append
    } catch {
        "Falha ao chamar $url : $_" | Out-File -FilePath $agentLog -Append
    }
}

Write-Host "Parte A concluida. Log salvo em $agentLog"

# Parte B: snapshots de /healthz e /status durante o piloto

"=== PILOTO 1H CAMPO - PARTE B (Snapshots backend) ===" | Out-File -FilePath $pilotLog -Encoding UTF8
"MachineId=$MachineId" | Out-File -FilePath $pilotLog -Append

$baseUrl = "http://127.0.0.1:8001"
$endpoints = @(
    "/healthz",
    "/v1/machines/{0}/status" -f $MachineId
)

for ($i = 1; $i -le 3; $i++) {
    $ts = Get-Date -Format "s"
    "`n--- Snapshot #$i em $ts ---" | Out-File -FilePath $pilotLog -Append
    foreach ($ep in $endpoints) {
        $url = "{0}{1}" -f $baseUrl, $ep
        "GET $url" | Out-File -FilePath $pilotLog -Append
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
            "HTTP $($resp.StatusCode)" | Out-File -FilePath $pilotLog -Append
            $resp.Content | Out-File -FilePath $pilotLog -Append
        } catch {
            "Falha ao chamar $url : $_" | Out-File -FilePath $pilotLog -Append
        }
    }

    if ($i -lt 3) {
        Write-Host "Aguardando 30 minutos antes do proximo snapshot... (Ctrl+C para pular)"
        Start-Sleep -Seconds (30*60)
    }
}

Write-Host "Piloto concluido. Logs salvos em:" 
Write-Host " - Agent:  $agentLog"
Write-Host " - Backend: $pilotLog"
