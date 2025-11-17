# Status – Missões 1 a 3 (Telemetry em Windows)

## Ambiente
- Windows version: Microsoft Windows NT 10.0.26200.0
- PowerShell version: 5.1.26100.7019 (Desktop)
- Python version (em uso): 3.11.9 (`python --version`)
- Diretório do projeto: `C:\cnc-telemetry-main`

## Preparação do backend
- `.venv` criado/confirmado em `C:\cnc-telemetry-main\.venv`
- `pip install --upgrade pip` executado sem erros
- `pip install -r backend/requirements.txt` concluído (todos os pacotes instalados/confirmados)

## Execução do backend (Missão 3)
- Comando: `python -m backend.server_entry`
- Resultado: servidor iniciou e logou `Uvicorn running on http://0.0.0.0:8001`
- Processo encerrado manualmente após teste (`Stop-Process -Id 8612`)

## Healthz
- URL testada: `http://localhost:8001/healthz`
- Comando: `Invoke-WebRequest -Uri http://localhost:8001/healthz -UseBasicParsing`
- Status HTTP: 200 OK
- Corpo: `{"status":"ok","service":"cnc-telemetry","version":"v0.3"}`

## Situação
✅ Missões 1–3 concluídas: ambiente verificado, venv configurado, backend em Windows respondendo /healthz 200.

## Missão 4 – start_telemetry.bat
- Arquivo criado: `scripts/start_telemetry.bat`
- Conteúdo base: ativa `.venv` e roda `python -m backend.server_entry` a partir de `C:\cnc-telemetry-main`
- Teste: executado via `cmd /c scripts\start_telemetry.bat` (PID 15948)
- Resultado: backend subiu e `/healthz` respondeu 200 conforme seção acima; processo encerrado com `Stop-Process -Id 15948`

## Missão 5 – Rede e firewall (pré-fábrica)
- IP detectado: `192.168.56.1` (salvo em `scripts/last_ip_port.txt`)
- Documentos criados: `docs/REDE_E_FIREWALL_TELEMETRY.txt` com passos para teste remoto e abertura de porta 8001
- Situação do teste: `/healthz` local já respondia 200; aguarda execução em segundo host para validar rota/firewall externo

## Missão 6 – install_telemetry.ps1 e instruções M80
- Script: `scripts/windows/install_telemetry.ps1` (confere Python, venv, deps, guia para subir backend e testar `/healthz`)
- Saída: `C:\cnc-telemetry\docs\CONFIGURAR_CNC_M80.txt` contendo IP, porta e checklist para orientar o técnico da M80

## Missão 7 – Firewall admin e teste remoto
- PowerShell elevado confirmado (sessão Administrador)
- Regra criada com sucesso: `New-NetFirewallRule ... -DisplayName "CNC Telemetry 8001"`
- IP vigente durante a missão: `192.168.56.1`
- Observação: tentativa de `Invoke-WebRequest http://localhost:8001/healthz` retornou "Impossível conectar-se" porque o backend não estava rodando; é necessário iniciar `scripts/start_telemetry.bat` antes do teste e repetir o `Invoke-WebRequest`
- Próximo passo: validar `/healthz` a partir de outro host assim que o backend estiver ativo

## Observações
- Próximos passos sugeridos: finalizar teste remoto (Missão 7) e avançar para Missão 9 (serviço Windows + modo demo).
