param(
    [string]$Port = "8001",
    [int]$DelaySeconds = 8
)

$ErrorActionPreference = "Stop"

Write-Host "Iniciando cnc-telemetry-gateway.exe..."
$exePath = Join-Path -Path (Resolve-Path ".") -ChildPath "dist\cnc-telemetry-gateway.exe"

if (-not (Test-Path $exePath)) {
    Write-Host "ERRO: Executável não encontrado em: $exePath"
    exit 1
}

$proc = Start-Process -FilePath $exePath -PassThru
Write-Host "PID iniciado:" $proc.Id

Write-Host "Aguardando $DelaySeconds segundos para subida do servidor..."
Start-Sleep -Seconds $DelaySeconds

$proc.Refresh()
if ($proc.HasExited) {
    Write-Host "⚠ O processo encerrou antes do teste HTTP. ExitCode:" $proc.ExitCode
    Write-Host "Sugestão: execute manualmente 'dist\\cnc-telemetry-gateway.exe' para inspecionar o erro."
    exit 1
}

try {
    $url = "http://localhost:$Port/healthz"
    Write-Host "Testando endpoint:" $url
    $resp = Invoke-WebRequest $url -TimeoutSec 5
    Write-Host "✅ Healthz status:" $resp.StatusCode
} catch {
    Write-Host "❌ Falha ao acessar /healthz:"
    Write-Host $_
    exit 1
} finally {
    if ($null -ne $proc -and -not $proc.HasExited) {
        Write-Host "Finalizando processo..."
        $proc | Stop-Process
    }
}
