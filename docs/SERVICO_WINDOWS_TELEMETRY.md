# Serviço Windows – CNC Telemetry

Orientações para executar o backend em segundo plano como serviço do Windows usando NSSM.

## Pré-requisitos
1. Windows 10/11 com PowerShell.
2. Projeto `C:\cnc-telemetry-main` atualizado.
3. Ambiente virtual criado e dependências instaladas:
   ```powershell
   cd C:\cnc-telemetry-main
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r .\backend\requirements.txt
   ```
4. NSSM disponível (ex.: `C:\tools\nssm\nssm.exe`).

## Instalação com NSSM
1. Abra PowerShell **como administrador**.
2. Execute:
   ```powershell
   cd C:\cnc-telemetry-main
   $nssm = "C:\tools\nssm\nssm.exe"
   $service = "CncTelemetryService"
   $pythonExe = "C:\cnc-telemetry-main\.venv\Scripts\python.exe"

   & $nssm install $service $pythonExe
   & $nssm set $service AppDirectory C:\cnc-telemetry-main
   & $nssm set $service AppParameters "-m backend.server_entry"
   & $nssm set $service Start SERVICE_AUTO_START
   & $nssm set $service DisplayName "CNC Telemetry Backend"
   & $nssm set $service Description "Backend FastAPI do CNC Telemetry"
   ```
3. Inicie o serviço:
   ```powershell
   & $nssm start $service
   ```

## Operação
- Para verificar status:
  ```powershell
  & $nssm status CncTelemetryService
  ```
- Para parar/iniciar:
  ```powershell
  & $nssm stop CncTelemetryService
  & $nssm start CncTelemetryService
  ```
- Para remover:
  ```powershell
  & $nssm remove CncTelemetryService confirm
  ```

## Logs e diagnóstico
1. Verifique `/healthz`:
   ```powershell
   Invoke-WebRequest http://localhost:8001/healthz
   ```
2. Use `scripts/windows/telemetry_diag.ps1` para checar ambiente, IPs e `/healthz`.
3. Caso o serviço não suba, consulte o Event Viewer (`Applications and Services Logs > nssm`).

## Integração com o modo demo
1. Garanta que o backend está ativo (serviço ou `start_telemetry.bat`).
2. Ative a venv e rode o script de eventos fake:
   ```powershell
   cd C:\cnc-telemetry-main
   .\.venv\Scripts\Activate.ps1
   $env:TELEMETRY_BASE_URL = "http://localhost:8001"  # ajuste se necessário
   $env:TELEMETRY_MACHINE_ID = "DEMO_MACHINE"
   python .\tools\demo\send_fake_events.py
   ```
3. Abra o painel/frontend para visualizar as mudanças simuladas (status, eventos, OEE).
4. Use este fluxo sempre que precisar demonstrar o sistema sem depender da CNC/M80.
