# Checklist de Visita — CNC Telemetry (Windows)

## 1. Antes de sair
- **Pendrive** contendo:
  - Última versão do repositório `cnc-telemetry` ou ZIP com build.
  - `scripts\windows\install_telemetry.ps1`.
  - `docs\REDE_E_FIREWALL_TELEMETRY.txt`.
  - `C:\cnc-telemetry\docs\CONFIGURAR_CNC_M80.txt` (imprimir e levar físico também).
- **Combinar com TI**:
  - PC Windows na mesma rede da CNC (M80).
  - Permissão para instalar/usar Python 3.10+ (se ainda não existir).
  - Permissão para abrir a porta **TCP 8001** na rede privada.
  - Usuário com privilégios administrativos (para regras de firewall/serviços).
- **Planejar demonstração**:
  - Opcional: levar script de demo (se existir) para mostrar painel mesmo sem CNC.

## 2. No PC do cliente
1. Copiar o kit para `C:\cnc-telemetry-main` (ou outro caminho acordado).
2. Abrir PowerShell **como administrador**.
3. Executar o instalador:
   ```powershell
   Set-Location C:\cnc-telemetry-main
   .\scripts\windows\install_telemetry.ps1
   ```
4. Seguir o fluxo do script:
   - Confirma projeto + Python.
   - Cria/usa `.venv` e instala deps.
   - Solicita subir `scripts\start_telemetry.bat` em outra janela.
   - Testa `http://localhost:8001/healthz` → esperar HTTP 200.
5. Se o teste local falhar, resolver antes de seguir (logs no console).

## 3. Com o time de TI
1. Rodar `ipconfig` e anotar o IP do PC Telemetry.
2. Criar (ou validar) regra de firewall permitindo **porta 8001/TCP** em rede privada:
   ```powershell
   New-NetFirewallRule -DisplayName "CNC Telemetry 8001" `
     -Direction Inbound -Protocol TCP -LocalPort 8001 `
     -Action Allow -Profile Private
   ```
3. De outro computador interno (ou workstation do TI), testar:
   ```powershell
   Invoke-WebRequest -Uri "http://IP_DO_PC:8001/healthz"
   ```
   - Esperado: HTTP 200.
   - Se não responder, checar firewall/roteamento.
4. Registrar quem autorizou e como ficou configurada a rede (DHCP vs IP fixo).

## 4. Com o técnico da CNC (M80)
1. Abrir o documento `C:\cnc-telemetry\docs\CONFIGURAR_CNC_M80.txt`.
2. Explicar que a CNC precisa enviar dados para:
   - IP do PC Telemetry.
   - Porta **8001**.
3. No painel M80:
   - Navegar até a configuração de rede/comunicação.
   - Criar/editar o destino apontando para IP/porta acima.
4. Salvar e reiniciar o módulo de comunicação, se necessário.
5. Rodar um programa de teste na CNC.
6. No PC Telemetry, monitorar o dashboard:
   - Verificar se o status muda (PRONTA → RODANDO etc.).
   - Conferir log de eventos e OEE (se aplicável).

## 5. Quando algo não aparecer
- Confirmar que `scripts\start_telemetry.bat` (ou serviço) está em execução.
- Checar se o IP do PC mudou (rodar `ipconfig`).
- Revalidar firewall/roteador (porta 8001 aberta?).
- Perguntar ao técnico se as configurações da CNC foram salvas e se a máquina está realmente gerando eventos.
- Ver os logs do backend (console ou serviço) para mensagens de erro.

## 6. Entregáveis pós-visita
- Atualizar `docs/STATUS_WINDOWS_DEV.md` com:
  - IP final do PC na fábrica.
  - Resultado do teste remoto `/healthz`.
  - Confirmação da regra de firewall.
  - Quais arquivos/configurações foram deixados com o cliente.
- Guardar cópias dos arquivos de instrução assinados/confirmados pelo TI e técnico, se possível.
- Planejar follow-up (monitoramento remoto ou segunda visita).
