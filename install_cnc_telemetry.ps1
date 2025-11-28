
<#
    install_cnc_telemetry.ps1
    Instalador one-shot do CNC Telemetry (Windows)
    Fluxo:
        1. Verifica pré-requisitos (Python, Node, npm, NSSM)
        2. Cria venv e instala dependências do backend
        3. Configura .env.beta (ou reaproveita existente)
        4. Build do frontend (se existir)
        5. Registra serviço Windows via NSSM e valida /healthz
#>

param(
    [string]$InstallDir = "C:\cnc-telemetry-main",
    [string]$PythonExe = "python",
    [string]$NodeExe = "node",
    [string]$NpmExe = "npm",
    [string]$NssmPath = "C:\nssm\nssm.exe",
    [int]$ApiPort = 8001,
    [string]$EnvTemplate = "C:\CNC-Telemetry-Kit\env\.env.beta.example"
)

$ErrorActionPreference = "Stop"
Write-Host "=== CNC Telemetry Installer ==="

function Assert-Command {
    param(
        [string]$Name,
        [string]$Command
    )
    Write-Host "Verificando $Name..."
    $exists = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $exists) {
        throw "Dependência ausente: $Name ('$Command') não encontrada no PATH."
    }
}

# 1) Pré-requisitos básicos
Assert-Command -Name "Python" -Command $PythonExe
Assert-Command -Name "Node"   -Command $NodeExe
Assert-Command -Name "npm"    -Command $NpmExe

function Assert-Nssm {
    param(
        [string]$Path
    )

    Write-Host "Verificando NSSM em '$Path'..."

    if (-not (Test-Path $Path)) {
        Write-Error @"
O instalador falhou logo na checagem inicial porque o NSSM não foi encontrado no caminho padrão '$Path'.

Para seguir, coloque o executável nesses diretórios (por exemplo, extraindo 'nssm-2.24.zip' para 'C:\nssm')
ou rode o script informando o caminho correto:

    .\install_cnc_telemetry.ps1 -NssmPath 'C:\onde\esta\nssm.exe'

Depois de ajustar, execute novamente este instalador.
"@
        exit 1
    }
}

Assert-Nssm -Path $NssmPath

if (-not (Test-Path $InstallDir)) {
    throw "Diretório $InstallDir não encontrado. Extraia ou clone o repositório antes de executar."
}

Set-Location $InstallDir
Write-Host "Diretório de instalação: $InstallDir"

$backendDir = Join-Path $InstallDir "backend"
$frontendDir = Join-Path $InstallDir "frontend"
if (-not (Test-Path $backendDir)) {
    throw "Pasta backend não encontrada em $InstallDir. Estrutura inválida."
}

# 2) Virtualenv
$venvPath = Join-Path $InstallDir ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Criando virtualenv em $venvPath..."
    & $PythonExe -m venv $venvPath
} else {
    Write-Host "Virtualenv já existe em $venvPath, reaproveitando."
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip    = Join-Path $venvPath "Scripts\pip.exe"
if (-not (Test-Path $venvPython)) {
    throw "python.exe não encontrado dentro do venv ($venvPython)."
}

# 3) Dependências backend
$requirements = Join-Path $backendDir "requirements.txt"
if (-not (Test-Path $requirements)) {
    throw "Arquivo requirements.txt não encontrado em $backendDir"
}
Write-Host "Instalando dependências do backend..."
& $venvPip install --upgrade pip
& $venvPip install -r $requirements

# 4) Configurar .env.beta
$envFile = Join-Path $backendDir ".env.beta"
if (-not (Test-Path $envFile)) {
    if (Test-Path $EnvTemplate) {
        Write-Host "Copiando template de $EnvTemplate para $envFile"
        Copy-Item $EnvTemplate $envFile -Force
    } else {
        Write-Host "Criando .env.beta padrão em $envFile"
        @"
TELEMETRY_DATABASE_URL=sqlite:///./telemetry_beta.db
TELEMETRY_API_HOST=0.0.0.0
TELEMETRY_API_PORT=$ApiPort
"@ | Out-File -FilePath $envFile -Encoding UTF8
    }
} else {
    Write-Host ".env.beta já existe em backend/, mantendo conteúdo atual."
}

# 5) Seed opcional (não falha se der erro)
try {
    Write-Host "Executando seed opcional (scripts/seed_beta_demo.py)..."
    & $venvPython -m scripts.seed_beta_demo
} catch {
    Write-Warning "Seed falhou: $_"
}

# 6) Frontend build (se existir)
if (Test-Path $frontendDir) {
    Write-Host "Instalando dependências e gerando build do frontend..."
    Set-Location $frontendDir
    & $NpmExe install
    & $NpmExe run build
    Set-Location $InstallDir
} else {
    Write-Host "Pasta frontend não encontrada, pulando build."
}

# 7) Registrar serviço via NSSM
$serviceName = "CncTelemetryService"
$backendMain = "main:app"
$uvicornArgs = "-m uvicorn $backendMain --host 0.0.0.0 --port $ApiPort"

Write-Host "Registrando serviço $serviceName..."
try {
    & $NssmPath stop $serviceName | Out-Null
    & $NssmPath remove $serviceName confirm | Out-Null
} catch {
    Write-Host "Serviço $serviceName ainda não existia, seguindo."
}

& $NssmPath install $serviceName $venvPython $uvicornArgs
& $NssmPath set $serviceName AppDirectory $backendDir
& $NssmPath set $serviceName DisplayName "CNC Telemetry Backend"
& $NssmPath set $serviceName Description "Backend FastAPI do CNC Telemetry"
& $NssmPath set $serviceName Start SERVICE_AUTO_START
& $NssmPath set $serviceName AppEnvironmentExtra "PYTHONPATH=$backendDir"

# Configurar políticas de restart automático
Write-Host "Configurando políticas de restart..."
& $NssmPath set $serviceName AppRestartDelay 30000
& $NssmPath set $serviceName AppThrottle 5000
& $NssmPath set $serviceName AppExit Default Restart
& $NssmPath set $serviceName AppRestartDelay 15000

# Configurar firewall Windows para permitir portas
Write-Host "Configurando firewall Windows..."
try {
    # Permitir porta API (8001)
    New-NetFirewallRule -DisplayName "CNC Telemetry API" -Direction Inbound -Protocol TCP -LocalPort $ApiPort -Action Allow -ErrorAction SilentlyContinue
    # Permitir porta Frontend (3000)
    New-NetFirewallRule -DisplayName "CNC Telemetry Frontend" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow -ErrorAction SilentlyContinue
    Write-Host "Regras de firewall criadas com sucesso."
} catch {
    Write-Warning "Falha ao configurar firewall (pode requerer administrador): $_"
}

Write-Host "Iniciando serviço..."
& $NssmPath start $serviceName

# 8) Teste rápido /healthz
Write-Host "Aguardando backend subir..."
Start-Sleep -Seconds 5
try {
    $health = Invoke-WebRequest -Uri "http://localhost:$ApiPort/healthz" -UseBasicParsing -TimeoutSec 5
    Write-Host "/healthz -> $($health.StatusCode)"
} catch {
    Write-Warning "Falha ao chamar /healthz: $_"
}

Write-Host "Instalação concluída. Verifique o serviço '$serviceName' em services.msc ou 'nssm status $serviceName'."
