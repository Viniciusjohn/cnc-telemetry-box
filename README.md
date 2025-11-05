# cnc-telemetry

Sistema de telemetria para máquinas CNC Mobile+PC com PWA instalável.

## 🎯 Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React + TypeScript + Vite
- **PWA:** Service Worker + Manifest
- **Testes:** Playwright
- **Protocolo:** MTConnect (padrão aberto)

---

## 📊 Métricas Coletadas

- **RPM** (rotação do spindle)
- **Feed** (mm/min)
- **Estado:** Running/Stopped (regra ≥15s)
- **Tempo de usinagem**

---

## 🚀 Quick Start

### Backend (porta 8001)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8001 --reload
```

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
