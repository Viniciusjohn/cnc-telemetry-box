Set-Location "$PSScriptRoot\..\..\frontend"

if (-not (Test-Path "package.json")) {
    Write-Error "package.json not found. Ensure you are in the frontend directory."
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies (npm install)..."
    npm install
}

Write-Host "Starting CNC Telemetry frontend (Vite dev server)..."
npm run dev
