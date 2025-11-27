#!/usr/bin/env pwsh
# Diagnostico basico do CNC Telemetry em Windows

$ErrorActionPreference = "Stop"

Write-Host "=== CNC TELEMETRY - DIAGNOSTICO BASICO WINDOWS ===`n"

# 1) Ambiente
Write-Host "[1/4] Ambiente"
Write-Host "PowerShell version:"
$PSVersionTable | Out-Host

Write-Host "`nPython version (se disponivel):"
try {
    python --version 2>&1 | Out-Host
} catch {
    Write-Host "[AVISO] Python nao encontrado no PATH."
}

# 2) Teste do /healthz local
Write-Host "`n[2/4] Testando /healthz em http://localhost:8001/healthz ..."
$healthUrl = "http://localhost:8001/healthz"
$code = $null
$body = $null
try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
    $code = $response.StatusCode
    $body = $response.Content
} catch {
    Write-Host "[ERRO] Nao foi possivel acessar $healthUrl"
    Write-Host "Detalhes:" $_.Exception.Message
}

if ($code -eq 200) {
    Write-Host "[OK] /healthz respondeu HTTP 200."
} else {
    Write-Host "[ALERTA] /healthz NAO respondeu 200. Codigo recebido:" $code
}

if ($body) {
    Write-Host "`nCorpo da resposta (primeiras linhas):"
    $body.Split("`n") | Select-Object -First 5 | Out-Host
}

# 3) IPs uteis
Write-Host "`n[3/4] IP atual desta maquina (enderecos IPv4 uteis):"
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1" }
    if ($ips) {
        foreach ($ip in $ips) {
            Write-Host ("Interface: {0}  IP: {1}" -f $ip.InterfaceAlias, $ip.IPAddress)
        }
    } else {
        Write-Host "[ALERTA] Nenhum IPv4 util encontrado (verificar conexao de rede)."
    }
} catch {
    Write-Host "[ERRO] Falha ao obter IPs:" $_.Exception.Message
}

# 4) Orientacao
Write-Host "`n[4/4] Interpretando o resultado:"
Write-Host "- Se /healthz local NAO respondeu 200, verifique se o backend esta rodando (start_telemetry.bat ou servico)."
Write-Host "- Se /healthz local respondeu 200, teste a partir de OUTRO host na mesma rede:" 
Write-Host "    Invoke-WebRequest -Uri \"http://IP_DA_MAQUINA:8001/healthz\""
Write-Host "    Se remoto falhar, suspeite de firewall/roteamento."

Write-Host "`n=== FIM DO DIAGNOSTICO BASICO ==="
