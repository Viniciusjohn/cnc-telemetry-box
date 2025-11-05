# 🚀 EXECUTAR AGORA — F2 Soak Test

**Status:** ✅ Código pronto para campo  
**Próximo:** Validar localmente (5 min → 30 min)

---

## 📋 Checklist Rápido

### Já Feito ✅
- [x] Backend FastAPI (porta 8001) com /ingest
- [x] Adapter MTConnect Python (`mtconnect_adapter.py`)
- [x] Simulador MTConnect local (porta 5000)
- [x] 4 ajustes de campo aplicados:
  - RotaryVelocity (não SpindleSpeed)
  - PathFeedrate mm/s → mm/min
  - Execution normalizado
  - /sample com sequência

### Falta Executar ⏳
- [ ] **AGORA:** Soak 5 min (simulador)
- [ ] Soak 30 min (simulador)
- [ ] Campo com Nestor

---

## ⚡ EXECUTAR AGORA (5 min)

### Terminal 1: Simulador MTConnect

```bash
cd /home/viniciusjohn/iot
python3 scripts/mtconnect_simulator.py --port 5000
```

**Aguardar:** `🤖 MTConnect Simulator rodando em http://0.0.0.0:5000`

---

### Terminal 2: Backend API

```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate
uvicorn app:app --port 8001 --reload
```

**Aguardar:** `Application startup complete.`

---

### Terminal 3: Validação Rápida

```bash
cd /home/viniciusjohn/iot

export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001

./scripts/validate_f2.sh
```

**Saída esperada:**
```
[1/5] Testando /probe...
✓ PASS - RotaryVelocity encontrado
✓ PASS - PathFeedrate encontrado
✓ PASS - Execution encontrado

[2/5] Testando /sample...
✓ PASS - nextSequence=12345

[3/5] Verificando unidades...
✓ PASS - PathFeedrate em mm/s

[4/5] Verificando estados...
✓ PASS - Execution='ACTIVE'

[5/5] Testando /ingest...
✓ PASS - HTTP 201

✓ VALIDAÇÃO COMPLETA
```

**✅ PASS:** Todos os testes passaram → continuar  
**❌ FAIL:** Algum teste falhou → investigar antes de prosseguir

---

### Terminal 4: Soak Test 5 min

```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate

export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=5

python3 mtconnect_adapter.py
```

**Aguardar 5 minutos...**

**Saída esperada:**
```
🚀 Adapter iniciado: http://localhost:5000 → http://localhost:8001
   Machine ID: CNC-SIM-001
   Polling: 2.0s

INFO:__main__:Descoberta: {'rpm': 's1', 'feed': 'f1', 'execution': 'e1'}

✅ #1 | RPM=4123.5 Feed=1245.6 State=running Seq=12345
✅ #2 | RPM=4089.2 Feed=1198.3 State=running Seq=12346
✅ #3 | RPM=4156.7 Feed=1189.4 State=running Seq=12347
...
✅ #148 | RPM=4201.3 Feed=1195.2 State=running Seq=12493
✅ #149 | RPM=4198.9 Feed=1202.8 State=running Seq=12494
✅ #150 | RPM=4205.1 Feed=1188.6 State=running Seq=12495

📊 Relatório Final
   Duração: 300s
   Amostras enviadas: 150
   Erros: 0
   Perda: 0.00%
```

**Critérios de Aceite:**
- ✅ Amostras enviadas: ~150 (5min × 30amostras/min)
- ✅ Perda: <0.5% (< 1 amostra perdida)
- ✅ Erros: 0

**Se PASS:** ✅ Avançar para 30 min  
**Se FAIL:** ❌ Investigar erros antes de continuar

---

## 🎯 Próximo: Soak 30 min

**Apenas se 5 min passou:**

```bash
# MESMO terminal 4 (adapter)
export DURATION_MIN=30
python3 mtconnect_adapter.py
```

**Aguardar 30 minutos...**

**Critérios de Aceite:**
- ✅ Amostras enviadas: ~900
- ✅ Perda: <0.5% (<5 amostras)
- ✅ Erros: 0
- ✅ Simulador não travou/crashou

**Se PASS:** ✅ **F2 validado localmente! Pronto para campo.**  
**Se FAIL:** ❌ Analisar log, ajustar intervalo ou count

---

## 🏭 Próximo: Campo com Nestor

### Informações Necessárias (pedir ao Nestor)

- [ ] Série da máquina: M70 / M700 / M80 / M800?
- [ ] IP da máquina CNC: `192.168.1.___`
- [ ] MTConnect Agent rodando? Porta?
- [ ] Janela de ≥2h sem interromper produção

### Comandos de Campo

**Ver:** `docs/CAMPO_GUIA_EXECUTIVO.md` (guia completo)

**Resumo:**
1. Descobrir Agent: `nmap -p 5000-5010 192.168.1.0/24`
2. Validar: `./scripts/validate_f2.sh` (com AGENT_URL real)
3. Soak 30 min: `python3 backend/mtconnect_adapter.py` (com AGENT_URL real)
4. Salvar relatório e validar com Nestor

---

## 📊 Métricas de Aceite F2

| Métrica | Meta | Como Verificar |
|---------|------|----------------|
| **Perda de amostras** | <0.5% | Relatório final do adapter |
| **p95 latência** | ≤2s | Logs (se implementado) |
| **Erros** | 0 | Relatório final: `Erros: 0` |
| **Coerência RPM/Feed** | ±1% | Comparar com painel físico no campo |
| **Continuidade** | 30 min | Sem crashes/timeouts |

---

## 🚨 Se Algo Falhar

### Validação falha (validate_f2.sh)

**Causa:** Backend não está rodando ou simulador não responde

**Solução:**
```bash
# Verificar processos
ps aux | grep uvicorn
ps aux | grep mtconnect_simulator

# Reiniciar se necessário
pkill -f uvicorn
pkill -f mtconnect_simulator

# Voltar ao Terminal 1 e 2
```

### Soak test com muitos erros

**Causa:** Rede lenta, backend sobrecarregado, ou intervalo muito curto

**Solução:**
```bash
# Aumentar intervalo de 2s para 3s
export POLL_INTERVAL=3.0

# Rodar novamente
python3 mtconnect_adapter.py
```

### Perda >0.5%

**Causa:** Problemas de conectividade ou sequência

**Solução:**
- Verificar logs para padrão de erros
- Se for sequência: verificar `/sample` retorna `nextSequence`
- Se for timeout: aumentar `timeout` no httpx (mtconnect_adapter.py linha 49)

---

## 📚 Documentação de Referência

### Implementação
- `backend/mtconnect_adapter.py` — Adapter principal (produção)
- `scripts/mtconnect_simulator.py` — Simulador para testes
- `scripts/validate_f2.sh` — Validação rápida (5 testes)

### Manuais
- `docs/MTConnect_COMPLIANCE.md` — Padrões MTConnect (4 ajustes)
- `docs/CAMPO_GUIA_EXECUTIVO.md` — Guia completo de campo
- `docs/F2_QUICKSTART.md` — Quick start com exemplos

### Geral
- `README.md` — Visão geral do projeto
- `SMOKE_READY.md` — Checklist completo S1+F2

---

## ✅ Quando Concluir F2

### Issues GitHub (abrir após validação local)

```bash
export REPO=viniciusjohn/cnc-telemetry

gh issue create -R $REPO --title "F0 — Descoberta técnica (Mitsubishi/Valfenger)" --label MVP --label "fase:F0" --body "Mapear série, IP/porta, MTConnect vs SDK, janela ≥2h. Aceite: docs/f0_descoberta.md."

gh issue create -R $REPO --title "F1 — API e domínio: /ingest e /status (FastAPI)" --label MVP --label "fase:F1" --body "POST /ingest; GET /status; regras running/stopped≥15s; headers fail-closed. Aceite: smoke curl -I PASS."

gh issue create -R $REPO --title "F2 — Adapter: simulador → MTConnect/SDK Mitsubishi" --label MVP --label "fase:F2" --body "Simulador 2s; MTConnect mapping; fallback SDK. Aceite: 30min ingestão; jitter p95<400ms; drift<200ms."

gh issue create -R $REPO --title "F3 — PWA (mobile+desktop): /dashboard operator|wall" --label MVP --label "fase:F3" --body "Views operator/wall; polling 2s; PWA instalável. Aceite: Lighthouse≥90; Playwright ≥25 amostras/60s."

gh issue create -R $REPO --title "F4 — Piloto de campo com Nestor (aceitação)" --label MVP --label "fase:F4" --body "30min lado a lado; atraso≤1s (p95≤2s); RPM/Feed ±1%; disponibilidade≥99%."
```

### Próxima Fase: F3

**Dashboard PWA consumindo dados reais:**
- Endpoint GET `/v1/machines/ABR-850/status`
- Polling 2s no frontend
- 4 cards atualizando (RPM, Feed, Status, Tempo)
- PWA instalável validado no mobile do Nestor

---

## 🎬 TL;DR — Comandos Mínimos

```bash
# Terminal 1
python3 scripts/mtconnect_simulator.py --port 5000

# Terminal 2
cd backend && source .venv/bin/activate && uvicorn app:app --port 8001 --reload

# Terminal 3 (validar)
export AGENT_URL=http://localhost:5000 API_URL=http://localhost:8001
./scripts/validate_f2.sh

# Terminal 4 (soak 5 min)
cd backend && source .venv/bin/activate
export AGENT_URL=http://localhost:5000 API_URL=http://localhost:8001 MACHINE_ID=CNC-SIM-001 DURATION_MIN=5
python3 mtconnect_adapter.py

# Se PASS → soak 30 min
export DURATION_MIN=30
python3 mtconnect_adapter.py
```

**Tempo total:** 5-10 min (validação) + 5 min (soak curto) + 30 min (soak longo) = **~40 min**

---

**✅ F2 pronto. EXECUTAR comandos acima para validar localmente antes de ir ao campo!**

**Última atualização:** 2025-11-05 02:19 UTC-03:00
