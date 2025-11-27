Set-Location "$PSScriptRoot\..\.."

$venvActivatePath = ".\backend\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivatePath)) {
    Write-Error "Virtual environment not found at backend/.venv. Execute python -m venv backend/.venv first."
    exit 1
}

. $venvActivatePath

$env:ENABLE_M80_WORKER = "true"
$env:USE_SIMULATION_DATA = "true"
$env:TELEMETRY_POLL_INTERVAL_SEC = "1"
$env:MACHINE_ID = "M80-DEMO-01"
$env:API_URL = "http://127.0.0.1:8001"

Write-Host "Starting CNC Telemetry backend in DEMO mode..."
python -m backend.server_entry
