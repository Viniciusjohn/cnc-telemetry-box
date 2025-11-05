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
echo ""

# Contador de amostras
count=0
errors=0
start_time=$(date +%s)
end_time=$((start_time + DURATION_MIN * 60))

while [ $(date +%s) -lt $end_time ]; do
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  request_start=$(date +%s%3N)
  
  # Fetch MTConnect current
  xml=$(curl -s "http://${AGENT_IP}:${AGENT_PORT}/current?path=//Path" 2>/dev/null || echo "")
  
  if [ -z "$xml" ]; then
    echo "❌ [${timestamp}] Erro ao buscar MTConnect"
    ((errors++))
    sleep $INTERVAL_SEC
    continue
  fi
  
  # Parse XML (usando xmlstarlet se disponível, senão grep simples)
  if command -v xmlstarlet &> /dev/null; then
    rpm=$(echo "$xml" | xmlstarlet sel -t -v "//RotaryVelocity[1]" 2>/dev/null || echo "0")
    feed_mm_s=$(echo "$xml" | xmlstarlet sel -t -v "//PathFeedrate[1]" 2>/dev/null || echo "0")
    exec=$(echo "$xml" | xmlstarlet sel -t -v "//Execution[1]" 2>/dev/null || echo "READY")
  else
    # Fallback: grep + sed (menos confiável)
    rpm=$(echo "$xml" | grep -oPm1 '(?<=<RotaryVelocity[^>]*>)[^<]+' || echo "0")
    feed_mm_s=$(echo "$xml" | grep -oPm1 '(?<=<PathFeedrate[^>]*>)[^<]+' || echo "0")
    exec=$(echo "$xml" | grep -oPm1 '(?<=<Execution[^>]*>)[^<]+' || echo "READY")
  fi
  
  # Converter feed mm/s → mm/min (se necessário)
  if command -v bc &> /dev/null; then
    feed_mm_min=$(echo "$feed_mm_s * 60" | bc)
  else
    feed_mm_min=$(awk "BEGIN {print $feed_mm_s * 60}")
  fi
  
  # Normalizar execution → state
  case "$exec" in
    ACTIVE) state="running" ;;
    READY|IDLE|WAITING) state="idle" ;;
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
    -H "X-Request-Id: $(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "req-${count}")" \
    -H "X-Contract-Fingerprint: 010191590cf1" \
    -d "$payload" 2>/dev/null || echo -e "\n000")
  
  http_code=$(echo "$response" | tail -1)
  request_end=$(date +%s%3N)
  latency=$((request_end - request_start))
  
  if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
    ((count++))
    echo "✅ [${timestamp}] #${count} | RPM=${rpm} Feed=${feed_mm_min} State=${state} | ${latency}ms"
  else
    echo "❌ [${timestamp}] HTTP ${http_code} | Latency: ${latency}ms"
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

# Aceite: perda <0.5%
if (( $(awk "BEGIN {print ($loss_pct < 0.5)}") )); then
  echo "✅ PASS: Perda <0.5%"
  exit 0
else
  echo "❌ FAIL: Perda ≥0.5%"
  exit 1
fi
