param(
    [string]$SourceScript = (Join-Path $PSScriptRoot "..\install_cnc_telemetry.ps1"),
    [string]$OutputExe    = (Join-Path $PSScriptRoot "..\dist\CNC-Telemetry-Installer.exe"),
    [string]$ProductName  = "CNC Telemetry Installer",
    [string]$CompanyName  = "CNC-Genius",
    [string]$ProductVersion = "1.0.0",
    [switch]$SkipModuleInstall
)

$ErrorActionPreference = "Stop"
Write-Host "=== Build CNC Telemetry .exe Installer ==="

function Ensure-Ps2Exe {
    if (Get-Command Invoke-PS2EXE -ErrorAction SilentlyContinue) {
        return
    }

    if (-not (Get-Module -ListAvailable -Name ps2exe)) {
        if ($SkipModuleInstall) {
            throw "Módulo ps2exe não encontrado. Instale manualmente ou execute o script sem -SkipModuleInstall."
        }

        Write-Host "Instalando módulo ps2exe (CurrentUser)..."
        Install-Module -Name ps2exe -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop
    }

    Import-Module ps2exe -ErrorAction Stop
}

$resolvedSource = Resolve-Path $SourceScript -ErrorAction Stop
$outputDir = Split-Path -Parent $OutputExe
if (-not (Test-Path $outputDir)) {
    Write-Host "Criando diretório de saída $outputDir"
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

Ensure-Ps2Exe

Write-Host "Empacotando $resolvedSource -> $OutputExe"
Invoke-PS2EXE -InputFile $resolvedSource -OutputFile $OutputExe -noConsole -Title $ProductName -Product $ProductName -CompanyName $CompanyName -ProductVersion $ProductVersion -Description "Instalador one-click para CNC Telemetry"

Write-Host "Installer pronto em $OutputExe"
