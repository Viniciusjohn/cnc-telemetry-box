# MTConnect Compliance — cnc-telemetry

**Status:** ✅ Implementado  
**Referência:** [docs.mtconnect.org](https://www.mtconnect.org/documents)

---

## 🎯 4 Ajustes para Campo

### 1. RotaryVelocity (não SpindleSpeed)

**Padrão MTConnect:**
- ✅ `RotaryVelocity` — DataItem canônico desde v1.2
- ❌ `SpindleSpeed` — Deprecated desde v1.2

**Unidade:** `REVOLUTION/MINUTE` (rev/min)

**Implementação:**
```python
# Priorizar RotaryVelocity
rpm_elem = root.find(".//RotaryVelocity")
if rpm_elem is None:
    rpm_elem = root.find(".//SpindleSpeed")  # Fallback legacy
    logger.warning("Usando SpindleSpeed (deprecated)")

rpm = float(rpm_elem.text) if rpm_elem is not None else 0.0
```

**Referência:** MTConnect Standard Part 2 - Devices, Section 8.2.3

---

### 2. PathFeedrate com Conversão mm/s → mm/min

**Padrão MTConnect:**
- DataItem: `PATH_FEEDRATE`
- Unidade canônica: `MILLIMETER/SECOND` (mm/s)

**API cnc-telemetry:**
- Campo: `feed_mm_min`
- Unidade: mm/min (minuto, não segundo)

**Conversão:**
```python
feed_elem = root.find(".//PathFeedrate")
feed_value = float(feed_elem.text)
units = feed_elem.get("units", "")

if "SECOND" in units:
    feed_mm_min = feed_value * 60  # mm/s → mm/min
else:
    feed_mm_min = feed_value  # Já é mm/min
```

**Motivo:** Backend usa `feed_mm_min` para consistência com painéis CNC tradicionais.

**Referência:** MTConnect Standard Part 2, Section 8.3.1

---

### 3. Normalização de Execution

**Estados Canônicos MTConnect:**

| MTConnect | API State | Descrição |
|-----------|-----------|-----------|
| `ACTIVE` | `running` | Executando programa (usinagem ativa) |
| `READY` | `idle` | Pronta, não executando |
| `PROGRAM_COMPLETED` | `idle` | Programa finalizado |
| `OPTIONAL_STOP` | `idle` | Parada opcional |
| `STOPPED` | `stopped` | Parada completa |
| `FEED_HOLD` | `stopped` | Pausa programada (hold button) |
| `INTERRUPTED` | `stopped` | Parada temporária (alarme, porta) |
| `PROGRAM_STOPPED` | `stopped` | Programa parado |

**Aliases Não-Canônicos (terceiros):**

| Alias | Normalizado → | API State |
|-------|---------------|-----------|
| `IDLE` | `READY` | `idle` |
| `WAITING` | `READY` | `idle` |
| `RUNNING` | `ACTIVE` | `running` |
| `EXECUTING` | `ACTIVE` | `running` |
| `PAUSED` | `FEED_HOLD` | `stopped` |
| `HOLD` | `FEED_HOLD` | `stopped` |

**Implementação:**
```python
EXECUTION_MAP = {
    "ACTIVE": "running",
    "READY": "idle",
    "STOPPED": "stopped",
    "FEED_HOLD": "stopped",
    # ... ver mtconnect_adapter.py para lista completa
}

state = EXECUTION_MAP.get(exec_value, "idle")  # Default: idle
```

**Referência:** MTConnect Standard Part 2, Section 11.4

---

### 4. /sample com Controle de Sequência

**Problema com /current:**
- Retorna apenas snapshot atual
- Pode perder mudanças entre polls (2s)
- Sem garantia de continuidade

**Solução: /sample + sequência:**

```bash
# 1º Request: Sem sequência (pega valores iniciais)
GET /sample?count=1

# Response:
# <Header ... nextSequence="12345" />

# 2º Request: A partir de nextSequence
GET /sample?from=12345&count=200

# Response:
# <Header ... nextSequence="12545" />
# (retorna até 200 amostras desde seq 12345)

# 3º Request: Continua de onde parou
GET /sample?from=12545&count=200
```

**Vantagens:**
- ✅ Continuidade garantida (sem perdas entre polls)
- ✅ Detecta eventos rápidos (<2s)
- ✅ Buffer do agente previne perdas durante reconexão
- ✅ `count=200` captura múltiplas amostras por request

**Implementação:**
```python
if self.next_sequence:
    url = f"{agent_url}/sample?from={self.next_sequence}&count=200"
else:
    url = f"{agent_url}/sample?count=1"

root = ET.fromstring(response.text)
header = root.find(".//Header")
self.next_sequence = int(header.get("nextSequence", 0))
```

**Referência:** MTConnect Standard Part 1 - Overview, Section 9.5

---

## 🧪 Validação

### Teste Local (Simulador)

```bash
# Terminal 1: Simulador MTConnect (porta 5000)
python3 scripts/mtconnect_simulator.py --port 5000

# Terminal 2: Backend API (porta 8001)
cd backend && source .venv/bin/activate
uvicorn app:app --port 8001 --reload

# Terminal 3: Adapter Python (30s para smoke test)
cd backend
export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=0.5

python3 mtconnect_adapter.py
```

**Output esperado:**
```
🚀 Adapter iniciado: http://localhost:5000 → http://localhost:8001
   Machine ID: CNC-SIM-001
   Polling: 2.0s
✅ #1 | RPM=4123.5 Feed=1245.6 State=running Seq=12345
✅ #2 | RPM=4089.2 Feed=1198.3 State=running Seq=12346
...
📊 Relatório Final
   Duração: 30s
   Amostras enviadas: 15
   Erros: 0
   Perda: 0.00%
```

### Teste com Bash Script (alternativa)

```bash
export AGENT_IP=localhost
export AGENT_PORT=5000
export API_BASE=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=1

./scripts/mtconnect_ingest_sample.sh
```

---

## 🏭 Mitsubishi no Campo

### Opção A (Preferencial): MTConnect Data Collector

**Produto:** Mitsubishi MTConnect Data Collector  
**Plataforma:** Edgecross (Windows)  
**Séries suportadas:** M70, M700, M80, M800

**Como verificar se está instalado:**
```bash
# Scan de rede (trocar subnet)
nmap -p 5000-5010 192.168.1.0/24

# Teste de conectividade
curl -s http://192.168.1.100:5000/probe | head -30

# Se retornar XML MTConnectDevices, está rodando!
```

**Solicitação ao cliente/TI:**
> "Preciso confirmar se há um MTConnect Agent ou Data Collector rodando na célula.  
> Produto: Mitsubishi MTConnect Data Collector (via Edgecross).  
> IP da máquina CNC: [192.168.1.XXX]  
> Porta esperada: 5000-5010"

**Referência:** [Mitsubishi Electric - MTConnect](https://www.mitsubishielectric.com/fa/products/cnc/)

### Opção B (Fallback): SDK Direto

Se não houver Data Collector:
- Avaliar instalação (requer licença Edgecross)
- OU usar SDK Mitsubishi (M700/M80 Series Ethernet API)
- ⚠️ SDK é proprietário e varia por série

---

## 📋 Checklist de Conformidade

### Padrões MTConnect
- [x] RotaryVelocity prioritário (SpindleSpeed como fallback)
- [x] PathFeedrate com detecção de unidade (mm/s → mm/min)
- [x] Execution normalizado para vocabulário canônico
- [x] /sample com controle de sequência (nextSequence)
- [x] Validação de outliers (RPM >30k, Feed >10k)
- [x] Logging de estados desconhecidos

### API cnc-telemetry
- [x] POST /v1/telemetry/ingest com idempotência (machine_id+timestamp)
- [x] Validação Pydantic (rpm 0-30k, feed 0-10k, state enum)
- [x] Headers canônicos (X-Contract-Fingerprint, X-Request-Id)
- [x] HTTP 201 Created (ou 200 OK se duplicado)

### Testes
- [ ] Smoke test local (simulador) 1 min: PASS
- [ ] Smoke test local (simulador) 30 min: PASS, perda <0.5%
- [ ] Descoberta de agente no campo (probe)
- [ ] Teste campo 5 min: PASS
- [ ] Teste campo 30 min: PASS, p95 ≤2s, perda <0.5%

---

## 🚨 Riscos Mitigados

### 1. Unidades Mistas
**Risco:** Feed em mm/s vs mm/min causa "serrilhado" na UI.  
**Mitigação:** ✅ Detectar `units` no XML e converter no adapter.

### 2. Estados Não-Padronizados
**Risco:** Adapters terceiros emitem "IDLE", "WAITING", etc.  
**Mitigação:** ✅ Tabela `EXECUTION_MAP` com aliases + log de desconhecidos.

### 3. Perda de Eventos
**Risco:** /current perde mudanças rápidas entre polls.  
**Mitigação:** ✅ /sample com sequência + count=200.

### 4. Outliers
**Risco:** RPM=999999 ou Feed=50000 passam validação.  
**Mitigação:** ✅ Validação no adapter (0-30k, 0-10k) + Pydantic no backend.

---

## 📚 Referências Técnicas

- **MTConnect Standard:** https://www.mtconnect.org/documents
- **MTConnect v1.8 (latest):** https://www.mtconnect.org/standard-download
- **Mitsubishi MTConnect:** https://www.mitsubishielectric.com/fa/products/cnc/
- **Edgecross Platform:** https://www.edgecross.org/

---

**Status:** ✅ Adapter pronto para campo. Aguardando confirmação de série/IP/Collector do Nestor.
