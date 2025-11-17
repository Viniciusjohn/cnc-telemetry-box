# CHEGUEI NO CLIENTE — CNC TELEMETRY (WINDOWS) — CHECKLIST V1

Objetivo: garantir que o CNC Telemetry esteja rodando em um PC/VM Windows antes de tocar na CNC (Mitsubishi M80/M8x).

---
## 1. Antes de sair de casa
- [ ] Projeto `cnc-telemetry-main` atualizado.
- [ ] Pendrive/kit contendo:
  - [ ] `scripts/windows/start_telemetry.bat`
  - [ ] `scripts/windows/telemetry_diag.ps1`
  - [ ] `docs/REDE_E_FIREWALL_TELEMETRY.txt`
  - [ ] `C:\cnc-telemetry\docs\CONFIGURAR_CNC_M80.txt`
- [ ] Confirmar com TI do cliente:
  - PC Windows na mesma rede da CNC
  - Permissão para instalar/usar Python 3.x
  - Liberação da porta 8001/TCP
  - Usuário com privilégios administrativos

---
## 2. No PC do cliente (Windows)
1. **Acesso**
   - [ ] Logar com usuário que possa instalar software e criar regras de firewall.
2. **Projeto no disco**
   - [ ] Copiar `cnc-telemetry-main` para `C:\cnc-telemetry-main` (ou outro caminho simples).
3. **Criar venv (se necessário)**
   ```powershell
   cd C:\cnc-telemetry-main
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r .\backend\requirements.txt
   ```
4. **Subir backend**
   ```powershell
   cd C:\cnc-telemetry-main
   .\scripts\windows\start_telemetry.bat
   ```
5. **Testar /healthz local**
   - Navegador ou PowerShell: `Invoke-WebRequest http://localhost:8001/healthz`
   - Esperado: HTTP 200 + JSON `{"status":"ok"...}`
   - Se falhar: corrigir ambiente antes de prosseguir.

---
## 3. Checklist de rede (IP + firewall)
1. **Descobrir IP do PC Telemetry**
   ```powershell
   ipconfig
   ```
   - Anotar o IPv4 da interface usada pela CNC.
2. **Testar de outro host** (quando possível):
   ```powershell
   Invoke-WebRequest http://IP_DO_PC:8001/healthz
   ```
   - Se local OK e remoto NÃO → falar com TI para liberar porta 8001/TCP.
3. **Regra de firewall**
   ```powershell
   New-NetFirewallRule -DisplayName "CNC Telemetry 8001" `
     -Direction Inbound -Protocol TCP -LocalPort 8001 `
     -Action Allow -Profile Private
   ```
   - Registrar quem autorizou.

---
## 4. Checklist na CNC (M80/M8x)
1. **Confirmar rede**
   - IP da CNC e máscara → deve estar na mesma faixa do PC Telemetry.
2. **Configurar destino**
   - IP do PC Telemetry
   - Porta 8001
3. **Salvar e aplicar**
   - Reiniciar comunicação se necessário.
4. **Rodar programa de teste**
   - Observar no PC: logs/eventos/status.

---
## 5. Se nada aparecer no painel
1. Ver se `start_telemetry.bat` está rodando (janela aberta, sem erro).
2. Re-testar `http://localhost:8001/healthz`.
3. Re-testar do host remoto (http://IP_DO_PC:8001/healthz). Se falhar, revisar firewall/TI.
4. Revisar configuração da CNC (IP/porta salvos?).

---
## 6. Plano B — Demo sem CNC
- Mostrar Telemetry rodando com `/healthz` 200.
- Explicar o que falta (porta liberada e CNC apontando pro IP).
- Combinar segunda visita focada em rede/TI.
- Com o backend rodando (serviço ou start_telemetry.bat), execute o script de demo:
  ```powershell
  cd C:\cnc-telemetry-main
  .\.venv\Scripts\Activate.ps1
  $env:TELEMETRY_BASE_URL = "http://localhost:8001"
  $env:TELEMETRY_MACHINE_ID = "DEMO_MACHINE"
  python .\tools\demo\send_fake_events.py
  ```
- Abra o painel e mostre os eventos/states simulados enquanto explica que, com a CNC apontando para esse IP/porta, os dados reais aparecerão da mesma forma.

---
## 7. Pós-visita
- Atualizar `docs/STATUS_WINDOWS_DEV.md` com IP final, status do firewall e teste remoto.
- Guardar logs/prints para documentação.
