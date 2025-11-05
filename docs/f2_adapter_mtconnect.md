# F2 — Adapter MTConnect: Mapeamento Canônico

**Status:** Em desenvolvimento  
**Aceite:** 30 min contínuos; p95 atraso ≤2s; RPM/Feed coerentes; Exec sem estados desconhecidos

---

## 📋 Mapeamento MTConnect → cnc-telemetry API

### Campos de Telemetria

| Campo API | MTConnect DataItem | Unidade | Conversão | Aliases Legacy |
|-----------|-------------------|---------|-----------|----------------|
| `rpm` | `RotaryVelocity` | rev/min | 1:1 | `SpindleSpeed` (deprecated ≥1.2) |
| `feed_mm_min` | `PathFeedrate` | mm/min | ×60 se mm/s | `Feedrate`, `Path/Feedrate/Actual` |
| `state` | `Execution` | enum | Normalizar → vocabulário | — |

### Vocabulário de Estados (`Execution`)

**MTConnect Canônico (docs.mtconnect.org):**
- `READY` → máquina pronta, não executando
- `ACTIVE` → executando programa (usinagem ativa)
- `INTERRUPTED` → parada temporária (alarme, porta aberta)
- `FEED_HOLD` → pausa programada (hold button)
- `STOPPED` → parada completa

**Mapeamento para API:**
```python
EXEC_MAP = {
    "ACTIVE": "running",
    "READY": "idle",
    "INTERRUPTED": "stopped",
    "FEED_HOLD": "stopped",
    "STOPPED": "stopped",
}

# Normalização de variantes não-canônicas
EXEC_ALIASES = {
    "IDLE": "READY",
    "WAITING": "READY",
    "RUNNING": "ACTIVE",
    "EXECUTING": "ACTIVE",
}
```

### Regra de "Máquina Parada" (≥15s)

**Critérios:**
1. `Execution` ∈ {`STOPPED`, `FEED_HOLD`, `INTERRUPTED`} por ≥15s, OU
2. `RotaryVelocity` ≈ 0 (tolerância ±5 rpm) por ≥15s

**Implementação:**
```python
def is_stopped(execution: str, rpm: float, duration_sec: int) -> bool:
    stopped_states = {"STOPPED", "FEED_HOLD", "INTERRUPTED"}
    
    if execution in stopped_states and duration_sec >= 15:
        return True
    if rpm <= 5 and duration_sec >= 15:
        return True
    
    return False
```

---

## 🔌 Descoberta de Agente MTConnect

### 1. Probe (Device Metadata)

```bash
# Descobrir IP/porta do agente (default: 5000)
curl -s http://<AGENT_IP>:5000/probe | head -50

# Extrair DataItems disponíveis
curl -s http://<AGENT_IP>:5000/probe \
  | xmllint --format - \
  | grep -E '(RotaryVelocity|PathFeedrate|Execution|SpindleSpeed)'
```

**Exemplo de resposta:**
```xml
<DataItem id="s1" name="Sspeed" type="ROTARY_VELOCITY" category="SAMPLE" units="REVOLUTION/MINUTE"/>
<DataItem id="f1" name="Frt" type="PATH_FEEDRATE" category="SAMPLE" units="MILLIMETER/SECOND"/>
<DataItem id="e1" name="exec" type="EXECUTION" category="EVENT"/>
```

### 2. Current (Valores Atuais)

```bash
# Buscar estado atual de todos os componentes
curl -s "http://<AGENT_IP>:5000/current?path=//Path" \
  | xmllint --format - \
  | sed -n '1,120p'

# Buscar apenas DataItems específicos
curl -s "http://<AGENT_IP>:5000/current?path=//DataItem[@type='ROTARY_VELOCITY']"
```

**Exemplo de resposta:**
```xml
<MTConnectStreams>
  <DeviceStream name="CNC-001">
    <ComponentStream component="Spindle">
      <Samples>
        <RotaryVelocity dataItemId="s1" timestamp="2025-11-05T05:06:00Z">4200</RotaryVelocity>
      </Samples>
    </ComponentStream>
    <ComponentStream component="Path">
      <Samples>
        <PathFeedrate dataItemId="f1" timestamp="2025-11-05T05:06:00Z" units="MILLIMETER/SECOND">14.2</PathFeedrate>
      </Samples>
      <Events>
        <Execution dataItemId="e1" timestamp="2025-11-05T05:06:00Z">ACTIVE</Execution>
      </Events>
    </ComponentStream>
  </DeviceStream>
</MTConnectStreams>
```

---

## 🏭 Mitsubishi: Rotas de Integração

### Rota A (Preferencial): MTConnect Data Collector

**Produto:** Mitsubishi MTConnect Data Collector (via Edgecross)  
**Plataforma:** Windows (edge PC ou IPC)  
**Documentação:** [Mitsubishi Electric - MTConnect](https://www.mitsubishielectric.com/fa/products/cnc/)

**Vantagens:**
- ✅ Protocolo MTConnect padrão (sem SDK proprietário)
- ✅ Suportado oficialmente pela Mitsubishi
- ✅ Expõe endpoints `/probe`, `/current`, `/sample`

**Verificação:**
```bash
# Procurar agente MTConnect na rede da célula
nmap -p 5000-5010 192.168.1.0/24

# Testar conectividade
curl -s http://192.168.1.100:5000/probe | head
```

### Rota B (Fallback): SDK Mitsubishi (M700/M80 Series)

**API:** MELFA-SDK ou M700 Series Ethernet API  
**Linguagem:** C/C++ com FFI para Python (ctypes)  
**Requer:** Biblioteca `.so` / `.dll` fornecida pela Mitsubishi

**Exemplo (pseudocódigo):**
```python
import ctypes

lib = ctypes.CDLL("libm700api.so")

# Conectar
conn_id = lib.m700_connect(b"192.168.1.100")

# Ler RPM
rpm = ctypes.c_int()
lib.m700_read_spindle_speed(conn_id, ctypes.byref(rpm))

# Ler Feed (pode vir como override %, precisa calcular feed real)
feed_override = ctypes.c_int()
lib.m700_read_feed_override(conn_id, ctypes.byref(feed_override))
# feed_real = programmed_feed * (feed_override / 100)
```

**Desvantagens:**
- ❌ Requer licença/contrato com Mitsubishi
- ❌ API proprietária (sem padrão aberto)
- ❌ Implementação específica por série (M70 ≠ M700 ≠ M80)

---

## 🧪 Teste de Ingestão (30 min)

### Script de Pull → POST (Polling 2s)

**Arquivo:** `scripts/mtconnect_ingest_test.sh`

```bash
#!/bin/bash
set -euo pipefail

AGENT_IP="${AGENT_IP:-192.168.1.100}"
AGENT_PORT="${AGENT_PORT:-5000}"
API_BASE="${API_BASE:-http://localhost:8001}"
MACHINE_ID="${MACHINE_ID:-ABR-850}"
INTERVAL_SEC=2
DURATION_MIN=30

echo "🔍 MTConnect Agent: http://${AGENT_IP}:${AGENT_PORT}"
echo "📡 API Backend: ${API_BASE}"
echo "⏱️  Duração: ${DURATION_MIN} min (polling ${INTERVAL_SEC}s)"
echo ""

# Contador de amostras
count=0
errors=0
start_time=$(date +%s)
end_time=$((start_time + DURATION_MIN * 60))

while [ $(date +%s) -lt $end_time ]; do
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  # Fetch MTConnect current
  xml=$(curl -s "http://${AGENT_IP}:${AGENT_PORT}/current?path=//Path" 2>/dev/null || echo "")
  
  if [ -z "$xml" ]; then
    echo "❌ [${timestamp}] Erro ao buscar MTConnect"
    ((errors++))
    sleep $INTERVAL_SEC
    continue
  fi
  
  # Parse XML (usando xmlstarlet)
  rpm=$(echo "$xml" | xmlstarlet sel -t -v "//RotaryVelocity[1]" 2>/dev/null || echo "0")
  feed_mm_s=$(echo "$xml" | xmlstarlet sel -t -v "//PathFeedrate[1]" 2>/dev/null || echo "0")
  exec=$(echo "$xml" | xmlstarlet sel -t -v "//Execution[1]" 2>/dev/null || echo "READY")
  
  # Converter feed mm/s → mm/min
  feed_mm_min=$(echo "$feed_mm_s * 60" | bc)
  
  # Normalizar execution
  case "$exec" in
    ACTIVE) state="running" ;;
    READY|IDLE) state="idle" ;;
    STOPPED|FEED_HOLD|INTERRUPTED) state="stopped" ;;
    *) state="idle" ;;
  esac
  
  # Payload JSON
  payload=$(cat <<EOF
{
  "machine_id": "$MACHINE_ID",
  "timestamp": "$timestamp",
  "rpm": $rpm,
  "feed_mm_min": $feed_mm_min,
  "state": "$state"
}
EOF
)
  
  # POST /ingest
  response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/v1/telemetry/ingest" \
    -H "Content-Type: application/json" \
    -H "X-Request-Id: $(uuidgen)" \
    -H "X-Contract-Fingerprint: 010191590cf1" \
    -d "$payload" 2>/dev/null || echo -e "\n000")
  
  http_code=$(echo "$response" | tail -1)
  
  if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
    ((count++))
    echo "✅ [${timestamp}] #${count} | RPM=${rpm} Feed=${feed_mm_min} State=${state}"
  else
    echo "❌ [${timestamp}] HTTP ${http_code} | Payload: ${payload}"
    ((errors++))
  fi
  
  sleep $INTERVAL_SEC
done

# Relatório
elapsed=$(($(date +%s) - start_time))
expected=$((DURATION_MIN * 60 / INTERVAL_SEC))
loss_pct=$(echo "scale=2; ($expected - $count) * 100 / $expected" | bc)

echo ""
echo "📊 Relatório de Ingestão (${DURATION_MIN} min)"
echo "   Amostras esperadas: ${expected}"
echo "   Amostras enviadas: ${count}"
echo "   Erros: ${errors}"
echo "   Perda: ${loss_pct}%"
echo "   Duração real: ${elapsed}s"

# Aceite: perda <0.5%
if (( $(echo "$loss_pct < 0.5" | bc -l) )); then
  echo "✅ PASS: Perda <0.5%"
  exit 0
else
  echo "❌ FAIL: Perda ≥0.5%"
  exit 1
fi
```

### Executar Teste

```bash
chmod +x scripts/mtconnect_ingest_test.sh

# Configurar variáveis
export AGENT_IP=192.168.1.100
export AGENT_PORT=5000
export API_BASE=http://localhost:8001
export MACHINE_ID=ABR-850

# Rodar teste (30 min)
./scripts/mtconnect_ingest_test.sh
```

**Métricas Esperadas:**
- ✅ p95 atraso ≤2s
- ✅ jitter p95 <400ms
- ✅ perda <0.5% em 30 min
- ✅ RPM/Feed coerentes (sem outliers absurdos)
- ✅ Execution sem estados desconhecidos

---

## 🚨 Riscos e Mitigações

### 1. MTConnect Agent Indisponível

**Risco:** Célula Mitsubishi sem MTConnect Data Collector instalado.

**Mitigação:**
- Solicitar instalação do produto oficial (Edgecross)
- Verificar licenças e compatibilidade de série (M70/M700/M80)
- Fallback: SDK Mitsubishi (Rota B)

### 2. Unidades Inconsistentes

**Risco:** `PathFeedrate` pode vir em mm/s ou mm/min dependendo do agente.

**Mitigação:**
```python
# Detectar unidade no XML
units = data_item.get("units", "")  # e.g., "MILLIMETER/SECOND"

if "SECOND" in units:
    feed_mm_min = feed_value * 60
elif "MINUTE" in units:
    feed_mm_min = feed_value
else:
    # Default: assumir mm/min
    feed_mm_min = feed_value
```

### 3. Estados Divergentes

**Risco:** Adapters de terceiros podem emitir estados não-canônicos.

**Mitigação:**
- Manter tabela de aliases (`EXEC_ALIASES`)
- Logar estados desconhecidos para análise
- Mapear para `idle` como fallback seguro

### 4. Latência de Rede

**Risco:** Polling de 2s pode ter jitter alto em redes congestionadas.

**Mitigação:**
- Medir p95 de latência no teste de 30 min
- Se p95 > 2s, aumentar intervalo ou usar streaming MTConnect

---

## ✅ Checklist de Aceite F2

- [ ] Confirmar série Mitsubishi (M70/M700/M80) com Nestor
- [ ] Descobrir MTConnect Agent (IP/porta ou confirmar ausência)
- [ ] Validar `/probe` retorna DataItems (RotaryVelocity, PathFeedrate, Execution)
- [ ] Implementar normalizador de unidades (mm/s → mm/min)
- [ ] Implementar normalizador de estados (aliases → vocabulário MTConnect)
- [ ] Rodar teste de 30 min: perda <0.5%, p95 ≤2s
- [ ] Validar RPM/Feed coerentes (sem outliers: RPM >50k, Feed >10k)
- [ ] Confirmar regra de "parada ≥15s" funciona corretamente
- [ ] Documentar estados desconhecidos encontrados (se houver)

---

## 📚 Referências

- **MTConnect Standard:** https://www.mtconnect.org/documents
- **MTConnect Probe/Current:** https://www.mtconnect.org/getting-started
- **Mitsubishi MTConnect:** https://www.mitsubishielectric.com/fa/products/cnc/
- **MTCUP (User Group):** Discussões sobre variantes de estados

---

**Próximo passo:** Aguardar confirmação do Nestor e implementar endpoint POST /v1/telemetry/ingest no backend.
