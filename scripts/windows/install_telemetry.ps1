Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== CNC Telemetry - install_telemetry.ps1 (ESQUELETO) ==="

# 1) Verificar diretório do projeto
$projectPath = "C:\cnc-telemetry-main"
if (-not (Test-Path $projectPath)) {
    Write-Host "Projeto não encontrado em $projectPath. Ajuste o caminho no script."
    exit 1
}
Set-Location $projectPath

# 2) Verificar Python
try {
    $pythonVersion = python --version
    Write-Host "Python detectado:" $pythonVersion
} catch {
    Write-Host "Python não encontrado. Instale Python 3.10+ e rode novamente."
    exit 1
}

# 3) Garantir venv e dependências
if (-not (Test-Path ".\.venv")) {
    Write-Host "Criando venv..."
    python -m venv .venv
}

Write-Host "Ativando venv e instalando dependências..."
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\backend\requirements.txt

# 4) Orientar a subir o servidor em outra janela
Write-Host ""
Write-Host "Abra outra janela e execute scripts\\start_telemetry.bat."
Write-Host "Quando o servidor estiver rodando (Uvicorn em 8001), pressione ENTER para testar /healthz."
Read-Host | Out-Null

$health = Invoke-WebRequest -Uri "http://localhost:8001/healthz" -UseBasicParsing
Write-Host "StatusCode /healthz:" $health.StatusCode
if ($health.StatusCode -ne 200) {
    Write-Host "Falha no teste de /healthz. Verifique se o servidor está rodando."
    exit 1
}

# 5) Descobrir IP e gerar instruções para M80
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1" } |
    Select-Object -First 1 -ExpandProperty IPAddress)
$port = 8001

Write-Host "IP detectado:" $ip
Write-Host "Porta Telemetry:" $port

$docsRoot = "C:\cnc-telemetry\docs"
New-Item -ItemType Directory -Path $docsRoot -Force | Out-Null

$instrPath = Join-Path $docsRoot "CONFIGURAR_CNC_M80.txt"
$instr = @"
CNC TELEMETRY — INSTRUÇÕES PARA CONFIGURAR A CNC (M80)

Este computador está pronto para receber dados da máquina.
IP do PC com Telemetry: $ip
Porta do Telemetry: $port

Quando estiver diante do controlador M80:
1. Garanta que a CNC e este PC estão na MESMA REDE.
2. No menu de comunicação/rede da M80, configure o destino apontando para:
   - IP de destino: $ip
   - Porta de destino: $port
3. Salve as configurações e rode um programa de teste.
4. Neste PC, confirme que o painel Telemetry reage (eventos/estado/OEE).

Se nada aparecer no painel Telemetry, verifique:
- Se scripts\start_telemetry.bat (ou serviço) está em execução.
- Se o IP deste PC mudou (rodar ipconfig novamente).
- Se o firewall do Windows permite conexões TCP na porta $port.
- Se a configuração da CNC foi salva corretamente (IP/porta).
"@
$instr | Set-Content -Path $instrPath -Encoding UTF8

Write-Host ""
Write-Host "Instalação básica concluída (esqueleto)."
Write-Host "Arquivo de instruções gerado em: $instrPath"
