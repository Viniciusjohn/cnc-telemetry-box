# Plano de Missões – Telemetry Pilot

## Missão 1 – Release limpa do piloto ✅

- **Objetivo**  
  Ter código congelado do Edge piloto (commit definido), sem WIP nem sujeira.
- **Entradas**  
  - `git status` limpo  
  - Stash/branch guardando WIP
- **Saídas**  
  - Hash do commit do piloto (`ff49a3c` + patches cirúrgicos)  
  - Anotação em DOSSIER com commit e data

---

## Missão 2 – Factory Mode (só MTConnect) ✅

- **Objetivo**  
  Garantir que o worker interno M80 **só** roda se `ENABLE_M80_WORKER=true`.
- **Entradas**  
  - Patch no `log_startup` e `config` (já aplicado)  
  - Backend iniciado com `ENABLE_M80_WORKER=false`
- **Saídas**  
  - `/healthz` mostrando `worker_m80_enabled=false`  
  - Logs do backend sem "M80 telemetry worker scheduled" no factory

---

## Missão 3 – Factory local (lab) ✅

- **Objetivo**  
  Provar backend local em factory mode com `/healthz` e `/status` válidos.
- **Entradas**  
  - Backend rodando em `http://127.0.0.1:8001`  
  - Sem worker (`ENABLE_M80_WORKER=false`)
- **Saídas**  
  - `curl /healthz` 200 com `worker_m80_enabled=false`  
  - `curl /v1/machines/M80-FABRICA-01/status` 200 com contrato correto

---

## Missão 4 – MTConnect em campo

### 4.a – Lab (VM + fake Agent) ✅

- **Objetivo**  
  Provar pipeline completo com Agent fake (rede/adapter/backend/UI).
- **Entradas**  
  - Agent fake em `192.168.3.14:5000` respondendo `/probe/current/sample`  
  - Adapter apontando para esse Agent  
  - Backend em factory mode
- **Saídas**  
  - Logs do adapter com `✅ #N ...` e `HTTP 201` em `/ingest`  
  - `/status` “respirando” (timestamp atualizando, modo AUTOMATIC)  
  - UI web conectada no backend local

### 4.b – Campo (Agent real) ⏳

- **Objetivo**  
  Provar 1h de estabilidade com Agent MTConnect real na rede do cliente.
- **Entradas**  
  - Roteiro de teste 1h (ping, `Test-NetConnection`, `curl /probe/current/sample`)  
  - Backend em factory mode  
  - Adapter com `AGENT_URL` e `MACHINE_ID` reais
- **Saídas**  
  - Logs do adapter (1h) com maioria 2xx e `✅`  
  - Amostras de `/healthz` e `/status` durante a hora  
  - Anotação de % de perda/timeouts e qualquer comportamento estranho

---

## Missão 5 – Robustez do adapter

### 5‑lite – Namespace MTConnect ✅

- **Objetivo**  
  Ler `ROTARY_VELOCITY`, `PATH_FEEDRATE`, `EXECUTION` mesmo com namespace.
- **Entradas**  
  - Patch namespace‑aware em `mtconnect_adapter.py` (já feito)
- **Saídas**  
  - `Descoberta` com IDs reais (não mais `None`)  
  - `rpm`/`feed_rate`/`execution` reais em `/status` com Agent compatível

### 5‑full – Resiliência de rede ⏳

- **Objetivo**  
  Lidar bem com ruído real: timeouts, 5xx, quedas longas do Agent.
- **Entradas**  
  - Resultado da 1h em campo (Missão 4.b)  
  - Padrões observados de falha
- **Saídas**  
  - Retry/backoff no adapter com limites razoáveis  
  - Estado “offline/degradado” quando N erros consecutivos  
  - Métrica simples de perda/% de falha no log ou `/healthz`

---

## Missão 6 – Auto-start no Windows ⏳

- **Objetivo**  
  Backend + adapter sobem sozinhos em boot/logon do gateway.
- **Entradas**  
  - Comando estável para backend em factory (`python -m backend.server_entry`)  
  - Comando estável para adapter (`python mtconnect_adapter.py` com envs)
- **Saídas**  
  - Tarefas no Task Scheduler para backend e adapter  
  - Teste de reboot: sem intervenção manual, `/healthz` e `/status` sobem

---

## Missão 7 – Build onedir + reboot ⏳

- **Objetivo**  
  Ter binário único do Edge e garantir reboot limpo.
- **Entradas**  
  - Configuração PyInstaller existente (`server_entry.py`)  
  - Pipeline de build onedir funcionando
- **Saídas**  
  - Binário onedir em pasta definida  
  - Task Scheduler apontando para o binário  
  - Teste de reboot bem-sucedido com `/healthz` OK

---

## Missão 8 – Baseline de 1 turno ⏳

- **Objetivo**  
  Coletar 1 turno (ex.: 8h) de dados estáveis em produção.
- **Entradas**  
  - Edge estável com autostart e reboot OK  
  - Janela combinada com o cliente
- **Saídas**  
  - Telemetria contínua no DB por um turno  
  - Resumo de uptime/tempo em corte/parada  
  - Registro de falhas de rede/Agent durante o turno

---

## Missão 9 – PMF v1 (relatório) ⏳

- **Objetivo**  
  Transformar o turno de baseline em um relatório legível.
- **Entradas**  
  - Dados do turno (Missão 8)  
  - Consultas prontas de OEE / histórico
- **Saídas**  
  - Relatório PMF v1 (markdown/PDF) com:  
    - gráfico simples de carga/estado  
    - principais paradas  
    - comentários sobre qualidade do sinal

---

## Missão 10 – Retomar Cloud/App ⏳

- **Objetivo**  
  Só depois do Edge “selado”, voltar para integrações cloud e app.
- **Entradas**  
  - Missões 1–9 carimbadas  
  - Plano de requisitos cloud (qual dashboard/alerta remoto faz sentido)
- **Saídas**  
  - Roadmap para deploy cloud/app  
  - Lista de ajustes necessários no frontend/backend para ambientes não‑locais
