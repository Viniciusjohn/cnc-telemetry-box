#!/bin/bash
set -euo pipefail

AGENT_IP="${AGENT_IP:-192.168.1.100}"
AGENT_PORT="${AGENT_PORT:-5000}"
API_BASE="${API_BASE:-http://localhost:8001}"
MACHINE_ID="${MACHINE_ID:-ABR-850}"
INTERVAL_SEC=2
DURATION_MIN="${DURATION_MIN:-30}"

echo "🔍 MTConnect Agent: http://${AGENT_IP}:${AGENT_PORT}"
echo "📡 API Backend: ${API_BASE}"
echo "⏱️  Duração: ${DURATION_MIN} min (polling ${INTERVAL_SEC}s)"
echo "📊 Modo: /sample com sequência incremental"
echo ""

# Contador de amostras
count=0
errors=0
start_time=$(date +%s)
end_time=$((start_time + DURATION_MIN * 60))

# Controle de sequência
next_sequence=""

# Função de normalização de estados
normalize_execution() {
  local exec=$1
  case "$exec" in
    ACTIVE) echo "running" ;;
    READY|PROGRAM_COMPLETED|OPTIONAL_STOP) echo "idle" ;;
    STOPPED|FEED_HOLD|INTERRUPTED|PROGRAM_STOPPED) echo "stopped" ;;
    # Aliases não-canônicos (terceiros)
    IDLE|WAITING) echo "idle" ;;
    RUNNING|EXECUTING) echo "running" ;;
    PAUSED|HOLD) echo "stopped" ;;
    *) 
      echo "⚠️  Estado desconhecido: $exec (mapeado para idle)" >&2
      echo "idle"
      ;;
  esac
}

while [ $(date +%s) -lt $end_time ]; do
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  request_start=$(date +%s%3N)
  
  # Fetch MTConnect /sample (com sequência se disponível)
  if [ -n "$next_sequence" ]; then
    url="http://${AGENT_IP}:${AGENT_PORT}/sample?from=${next_sequence}&count=200"
  else
    url="http://${AGENT_IP}:${AGENT_PORT}/sample?count=1"
  fi
  
  xml=$(curl -s "$url" 2>/dev/null || echo "")
  
  if [ -z "$xml" ]; then
    echo "❌ [${timestamp}] Erro ao buscar MTConnect /sample"
    ((errors++))
    sleep $INTERVAL_SEC
    continue
  fi
  
  # Capturar nextSequence do header
  if command -v xmlstarlet &> /dev/null; then
    next_sequence=$(echo "$xml" | xmlstarlet sel -t -v "//@nextSequence" 2>/dev/null || echo "")
  else
    next_sequence=$(echo "$xml" | grep -oPm1 '(?<=nextSequence=")[^"]+' || echo "")
  fi
  
  # Parse XML (priorizar RotaryVelocity sobre SpindleSpeed)
  if command -v xmlstarlet &> /dev/null; then
    rpm=$(echo "$xml" | xmlstarlet sel -t -v "//RotaryVelocity[1]" 2>/dev/null || \
          echo "$xml" | xmlstarlet sel -t -v "//SpindleSpeed[1]" 2>/dev/null || echo "0")
    feed_mm_s=$(echo "$xml" | xmlstarlet sel -t -v "//PathFeedrate[1]" 2>/dev/null || echo "0")
    exec=$(echo "$xml" | xmlstarlet sel -t -v "//Execution[1]" 2>/dev/null || echo "READY")
    units=$(echo "$xml" | xmlstarlet sel -t -v "//PathFeedrate[1]/@units" 2>/dev/null || echo "")
  else
    # Fallback: grep + sed
    rpm=$(echo "$xml" | grep -oPm1 '(?<=<RotaryVelocity[^>]*>)[^<]+' || \
          echo "$xml" | grep -oPm1 '(?<=<SpindleSpeed[^>]*>)[^<]+' || echo "0")
    feed_mm_s=$(echo "$xml" | grep -oPm1 '(?<=<PathFeedrate[^>]*>)[^<]+' || echo "0")
    exec=$(echo "$xml" | grep -oPm1 '(?<=<Execution[^>]*>)[^<]+' || echo "READY")
    units=$(echo "$xml" | grep -oPm1 '(?<=units=")[^"]+' | head -1 || echo "")
  fi
  
  # Converter PathFeedrate para mm/min (padrão MTConnect é mm/s)
  if command -v bc &> /dev/null; then
    if [[ "$units" == *"SECOND"* ]] || [ -z "$units" ]; then
      # mm/s → mm/min (×60)
      feed_mm_min=$(echo "$feed_mm_s * 60" | bc)
    else
      # Já é mm/min
      feed_mm_min=$feed_mm_s
    fi
  else
    # Usar awk se bc não disponível
    if [[ "$units" == *"SECOND"* ]] || [ -z "$units" ]; then
      feed_mm_min=$(awk "BEGIN {print $feed_mm_s * 60}")
    else
      feed_mm_min=$feed_mm_s
    fi
  fi
  
  # Normalizar Execution → state
  state=$(normalize_execution "$exec")
  
  # Validar faixas (detectar outliers)
  if (( $(awk "BEGIN {print ($rpm > 30000)}") )); then
    echo "⚠️  [${timestamp}] RPM outlier: ${rpm} (ignorando amostra)" >&2
    ((errors++))
    sleep $INTERVAL_SEC
    continue
  fi
  
  if (( $(awk "BEGIN {print ($feed_mm_min > 10000)}") )); then
    echo "⚠️  [${timestamp}] Feed outlier: ${feed_mm_min} (ignorando amostra)" >&2
    ((errors++))
    sleep $INTERVAL_SEC
    continue
  fi
  
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
    -H "X-Request-Id: $(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "req-${count}")" \
    -H "X-Contract-Fingerprint: 010191590cf1" \
    -d "$payload" 2>/dev/null || echo -e "\n000")
  
  http_code=$(echo "$response" | tail -1)
  request_end=$(date +%s%3N)
  latency=$((request_end - request_start))
  
  if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
    ((count++))
    echo "✅ [${timestamp}] #${count} | RPM=${rpm} Feed=${feed_mm_min} Exec=${exec}→${state} Seq=${next_sequence} | ${latency}ms"
  else
    body=$(echo "$response" | head -n -1)
    echo "❌ [${timestamp}] HTTP ${http_code} | ${body} | Latency: ${latency}ms"
    ((errors++))
  fi
  
  sleep $INTERVAL_SEC
done

# Relatório
elapsed=$(($(date +%s) - start_time))
expected=$((DURATION_MIN * 60 / INTERVAL_SEC))
loss_pct=$(awk "BEGIN {printf \"%.2f\", ($expected - $count) * 100 / $expected}")

echo ""
echo "📊 Relatório de Ingestão (${DURATION_MIN} min)"
echo "   Amostras esperadas: ${expected}"
echo "   Amostras enviadas: ${count}"
echo "   Erros: ${errors}"
echo "   Perda: ${loss_pct}%"
echo "   Duração real: ${elapsed}s"
echo "   Última sequência: ${next_sequence}"

# Aceite: perda <0.5%
if (( $(awk "BEGIN {print ($loss_pct < 0.5)}") )); then
  echo "✅ PASS: Perda <0.5%"
  exit 0
else
  echo "❌ FAIL: Perda ≥0.5%"
  exit 1
fi
