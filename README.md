# CNC-Genius Telemetria

Serviço de telemetria CNC do projeto CNC-Genius (MTConnect → JSON canônico → dashboard).

## 🎯 Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React + TypeScript + Vite
- **PWA:** Service Worker + Manifest
- **Testes:** Playwright
- **Protocolo:** MTConnect (padrão aberto)

---

## Sobre este repositório  — CNC Telemetry Box (Linux + Docker + Postgres)

Este repositório empacota o servidor de telemetria CNC existente em um formato próprio para um **appliance Linux headless**, chamado **CNC Telemetry Box**:

- Execução em um mini-PC ou servidor Linux dedicado na rede da fábrica.
- Todos os componentes (db, backend, adapter(s), sync, frontend) rodando em **containers Docker**.
- Banco padrão **PostgreSQL** para armazenamento local de histórico.
- Dashboard web local acessível via HTTP a partir da LAN da fábrica.

Para uma descrição funcional do produto e dos limites de capacidade do Box v1, consulte:

- `docs/CNC_TELEMETRY_BOX_V1.md` — visão geral do **CNC Telemetry Box v1 — gateway local de telemetria CNC**.

Este layout de Box Linux complementa o modo Windows já documentado em `docs/STATUS_WINDOWS_DEV.md` e `docs/DEPLOY_BETA_WINDOWS.md`, permitindo evoluir o mesmo backend para produção em fábrica.

---

## Como clonar e subir o CNC Telemetry Box (Linux + Docker + Postgres)

Mini-servidor de telemetria CNC para rodar como **appliance Linux headless**,
usando **Docker + Docker Compose + PostgreSQL**.

Documentação funcional do produto:
- `docs/CNC_TELEMETRY_BOX_V1.md`

### 1. Clonar o repositório

```bash
git clone https://github.com/Viniciusjohn/cnc-telemetry-box.git
cd cnc-telemetry-box
```

### 2. Criar o arquivo `.env`

```bash
cp .env.example .env
# editar a senha de banco em .env (POSTGRES_PASSWORD)
```

### 3. Subir o stack completo (db + backend + adapter + sync + frontend)

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8001/healthz
```

Se tudo estiver OK:

- O backend responde em `http://localhost:8001/healthz` com JSON `status: ok`.
- O adapter demo começa a enviar eventos para `/v1/telemetry/ingest`.
- O worker de sync imprime heartbeats periódicos (stub).

### 4. Acessar a UI do Box

No próprio servidor (ou em outro PC na mesma rede):

- Abrir no navegador: `http://<IP_DO_BOX>/`

A UI do CNC Telemetry Box será servida pelo container `frontend` na porta 80.

---

## 📊 Métricas Coletadas

- **RPM** (rotação do spindle)
- **Feed** (mm/min)
- **Estado:** Running/Stopped (regra ≥15s)
- **Tempo de usinagem**

---

## 🚀 Quick Start

### Backend (porta 8001)

#### Linux/macOS
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

#### Windows (modo rápido)
```powershell
cd C:\cnc-telemetry-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
```
- Subir backend: `scripts\windows\start_telemetry.bat`
- Diagnóstico: `scripts\windows\telemetry_diag.ps1`
- Instalação one-click: `install_cnc_telemetry.ps1` (detalhes em docs/STATUS_WINDOWS_DEV.md)
- Serviço Windows via NSSM: `scripts\windows\install_service_with_nssm.ps1` (docs/SERVICO_WINDOWS_TELEMETRY.md)
- Modo demo (sem CNC): `python tools\demo\send_fake_events.py` com o backend/serviço ativo

### Frontend (porta 5173)

```bash
cd frontend
npm install
npm run dev
```

**Acessar:** http://localhost:5173

---

## 🧪 Testes Locais (sem máquina real)

### 1. Simulador MTConnect

```bash
python3 scripts/mtconnect_simulator.py --port 5000
```

### 2. Adapter Python (30s)

```bash
cd backend
source .venv/bin/activate

export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=0.5

python3 mtconnect_adapter.py
```

**Saída esperada:**
```
✅ #1 | RPM=4123.5 Feed=1245.6 State=running Seq=12345
✅ #2 | RPM=4089.2 Feed=1198.3 State=running Seq=12346
...
📊 Relatório Final
   Amostras enviadas: 15
   Erros: 0
   Perda: 0.00%
```

---

## 📄 Documentação

### Geral
- `docs/ORIENTACOES.md` — Planejamento inicial (Cursor Rules, MCP, Gates)
- `SMOKE_READY.md` — Checklist de smoke test S1 + F2
- `.cursor/rules/` — Regras do Cursor isoladas por workspace

### F2 Adapter MTConnect
- `docs/MTConnect_COMPLIANCE.md` — ⭐ **Padrões canônicos (4 ajustes de campo)**
- `docs/F2_QUICKSTART.md` — Guia rápido de testes
- `docs/f2_adapter_mtconnect.md` — Documentação técnica completa

### APIs
- `POST /v1/telemetry/ingest` — Ingerir dados (idempotência: machine_id+timestamp)
- `GET /v1/machines/{id}/status` — Status individual
- `GET /v1/machines/status?view=grid` — Visão consolidada

---

## 🏭 Mitsubishi no Campo

### Preferencial: MTConnect Data Collector

**Produto:** Mitsubishi MTConnect Data Collector (Edgecross)  
**Séries:** M70, M700, M80, M800

**Como verificar:**
```bash
# Scan de rede
nmap -p 5000-5010 192.168.1.0/24

# Teste
curl -s http://192.168.1.100:5000/probe | head -30
```

**Fallback:** SDK Mitsubishi (proprietário, varia por série)

---

## ✅ Status do Projeto

### S1 (Semana 1) — ✅ COMPLETO
- Backend FastAPI com headers canônicos (X-Contract-Fingerprint, no-store, etc.)
- CORS + preflight OPTIONS 204
- Frontend PWA instalável (manifest + SW)
- Playwright instalado

### F2 (Adapter MTConnect) — ✅ PRONTO PARA CAMPO
- ✅ RotaryVelocity (não SpindleSpeed deprecated)
- ✅ PathFeedrate com conversão mm/s → mm/min
- ✅ Execution normalizado (vocabulário MTConnect)
- ✅ /sample com controle de sequência
- ✅ Simulador local funcional
- ✅ Adapter Python robusto (`mtconnect_adapter.py`)
- ⏸️ Aguardando: Série/IP do Nestor

### F3-F4 — PRÓXIMAS FASES
- F3: Dashboard consumindo dados reais
- F4: Piloto 30 min com aceitação

---

## 🎯 Aceite de F2

**Critérios:**
- ✅ 30 min de ingestão contínua
- ✅ p95 atraso ≤2s
- ✅ jitter p95 <400ms
- ✅ perda <0.5%
- ✅ RPM/Feed sem outliers (0-30k, 0-10k)
- ✅ Estados MTConnect normalizados

**Comando:**
```bash
export AGENT_URL=http://192.168.1.100:5000
export API_URL=http://localhost:8001
export MACHINE_ID=ABR-850
export DURATION_MIN=30

cd backend
source .venv/bin/activate
python3 mtconnect_adapter.py
```

---

## 📚 Referências

- **MTConnect Standard:** https://www.mtconnect.org/documents
- **Mitsubishi MTConnect:** https://www.mitsubishielectric.com/fa/products/cnc/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Playwright:** https://playwright.dev/

---

## Estrutura de diretórios

```text
cnc-telemetry-main/
  backend/               # FastAPI, app principal da telemetria
  frontend/              # UI (React/Vite) – package.json fica aqui
  deploy/                # scripts e arquivos de deploy (Linux/Windows/VM)
  scripts/               # scripts utilitários (seed, ferramentas, etc.)
  docs/
    analysis/            # análises técnicas
    plans/               # planos e roadmaps
    sprint_history/      # histórico de sprints e arquivos EXECUTAR_*
  archives/              # materiais antigos/experimentais (não usados em produção)
  .cursor/               # regras e configs do Cursor
  .gitignore
  README.md
  install_cnc_telemetry.ps1
```

Arquivos de sprint/planejamento (EXECUTAR_*, SPRINT_*, TODO_*, NEXT_STEPS, etc.) foram movidos para `docs/sprint_history/` ou `docs/analysis/` para manter a raiz limpa e adequada aos scripts de instalação e automação.

---

## 🔧 Ferramentas

### Backend
- `backend/app.py` — API FastAPI
- `backend/mtconnect_adapter.py` — Adapter MTConnect (produção)
- `backend/requirements.txt` — Dependências Python

### Frontend
- `frontend/src/App.tsx` — Dashboard 4 cards + polling 2s
- `frontend/public/manifest.webmanifest` — PWA manifest
- `frontend/public/sw.js` — Service Worker

### Scripts
- `scripts/mtconnect_simulator.py` — Simulador MTConnect local
- `scripts/mtconnect_ingest_sample.sh` — Teste bash com /sample
- `scripts/mtconnect_ingest_test.sh` — Teste bash com /current (legacy)

### Testes
- `frontend/e2e/smoke.spec.ts` — Playwright smoke test

---

## 🚨 Termo-Ban

**❌ NÃO REFERENCIAR:** CNC-Genius (projeto anterior)

Conforme `.cursor/rules/000_base.md`, este projeto é isolado e não deve importar código, políticas ou artefatos do CNC-Genius.

---

## 📞 Próximo Passo

**Aguardando Nestor:**
- [ ] Série da máquina (M70/M700/M80?)
- [ ] IP da máquina CNC
- [ ] Confirmar se há MTConnect Agent/Collector rodando
- [ ] Janela de ≥2h para testes sem interromper produção

**Quando confirmado:**
```bash
# 1. Descobrir agente
curl -s http://<IP>:5000/probe | head

# 2. Teste 30 min
export AGENT_URL=http://<IP>:5000
export DURATION_MIN=30
python3 backend/mtconnect_adapter.py
```

---

**Última atualização:** 2025-11-05 02:12 UTC-03:00
