<#
stop_factory.ps1
FieldKit: encerra backend + adapter iniciados por start_factory_1click.ps1
#>

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

$logsDir = Join-Path $scriptRoot "logs"
$pidFile = Join-Path $logsDir "factory_pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "[AVISO] Arquivo de PIDs nao encontrado em $pidFile. Nada para parar?"
    exit 0
}

try {
    $info = Get-Content $pidFile -Raw | ConvertFrom-Json
} catch {
    Write-Host ("[ERRO] Nao foi possivel ler {0}: {1}" -f $pidFile, $_)
    exit 1
}

$stopped = @()

if ($info.BackendPid) {
    $p = Get-Process -Id $info.BackendPid -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "Parando backend PID $($info.BackendPid)..."
        Stop-Process -Id $info.BackendPid -Force -ErrorAction SilentlyContinue
        $stopped += $info.BackendPid
    } else {
        Write-Host "[INFO] Backend PID $($info.BackendPid) nao encontrado (ja parado?)."
    }
}

if ($info.AdapterPid) {
    $p = Get-Process -Id $info.AdapterPid -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "Parando adapter PID $($info.AdapterPid)..."
        Stop-Process -Id $info.AdapterPid -Force -ErrorAction SilentlyContinue
        $stopped += $info.AdapterPid
    } else {
        Write-Host "[INFO] Adapter PID $($info.AdapterPid) nao encontrado (ja parado?)."
    }
}

$archiveName = "factory_pids_{0}_stopped.json" -f (Get-Date -Format "yyyyMMdd_HHmmss")
$archivePath = Join-Path $logsDir $archiveName
Move-Item -Path $pidFile -Destination $archivePath -Force

Write-Host "Stop concluido. PIDs parados: $($stopped -join ', ')"
Write-Host "Arquivo de PIDs arquivado em: $archivePath"
