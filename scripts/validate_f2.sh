#!/bin/bash
set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

AGENT_URL="${AGENT_URL:-http://localhost:5000}"
API_URL="${API_URL:-http://localhost:8001}"

echo "═══════════════════════════════════════════════════════"
echo "  F2 Validation — MTConnect Adapter"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Agent: $AGENT_URL"
echo "API:   $API_URL"
echo ""

# Teste 1: Probe (descoberta)
echo -e "${YELLOW}[1/5]${NC} Testando /probe (descoberta de DataItems)..."
probe_response=$(curl -s "$AGENT_URL/probe" 2>/dev/null || echo "")

if [ -z "$probe_response" ]; then
    echo -e "${RED}✗ FAIL${NC} - Agent não responde em /probe"
    exit 1
fi

# Verificar DataItems
if echo "$probe_response" | grep -q "RotaryVelocity"; then
    echo -e "${GREEN}✓ PASS${NC} - RotaryVelocity encontrado (canônico)"
elif echo "$probe_response" | grep -q "SpindleSpeed"; then
    echo -e "${YELLOW}⚠ WARN${NC} - SpindleSpeed encontrado (deprecated, ok como fallback)"
else
    echo -e "${RED}✗ FAIL${NC} - Nenhum DataItem de RPM encontrado"
fi

if echo "$probe_response" | grep -q "PathFeedrate"; then
    echo -e "${GREEN}✓ PASS${NC} - PathFeedrate encontrado"
else
    echo -e "${RED}✗ FAIL${NC} - PathFeedrate não encontrado"
fi

if echo "$probe_response" | grep -q "Execution"; then
    echo -e "${GREEN}✓ PASS${NC} - Execution encontrado"
else
    echo -e "${RED}✗ FAIL${NC} - Execution não encontrado"
fi

echo ""

# Teste 2: /sample com sequência
echo -e "${YELLOW}[2/5]${NC} Testando /sample com sequência..."
sample_response=$(curl -s "$AGENT_URL/sample?count=1" 2>/dev/null || echo "")

if [ -z "$sample_response" ]; then
    echo -e "${RED}✗ FAIL${NC} - /sample não responde"
    exit 1
fi

# Extrair nextSequence
if command -v xmlstarlet &> /dev/null; then
    next_seq=$(echo "$sample_response" | xmlstarlet sel -t -v "//@nextSequence" 2>/dev/null || echo "")
else
    next_seq=$(echo "$sample_response" | grep -oPm1 '(?<=nextSequence=")[^"]+' || echo "")
fi

if [ -n "$next_seq" ]; then
    echo -e "${GREEN}✓ PASS${NC} - nextSequence=$next_seq"
else
    echo -e "${RED}✗ FAIL${NC} - nextSequence não encontrado"
    exit 1
fi

echo ""

# Teste 3: Unidades (PathFeedrate)
echo -e "${YELLOW}[3/5]${NC} Verificando unidades..."

if echo "$sample_response" | grep -q "MILLIMETER/SECOND"; then
    echo -e "${GREEN}✓ PASS${NC} - PathFeedrate em mm/s (padrão MTConnect)"
elif echo "$sample_response" | grep -q "MILLIMETER/MINUTE"; then
    echo -e "${YELLOW}⚠ WARN${NC} - PathFeedrate em mm/min (não padrão, mas ok)"
else
    echo -e "${YELLOW}⚠ INFO${NC} - Unidade de PathFeedrate não detectada"
fi

echo ""

# Teste 4: Estados Execution
echo -e "${YELLOW}[4/5]${NC} Verificando estados Execution..."

if command -v xmlstarlet &> /dev/null; then
    exec_state=$(echo "$sample_response" | xmlstarlet sel -t -v "//Execution[1]" 2>/dev/null || echo "")
else
    exec_state=$(echo "$sample_response" | grep -oPm1 '(?<=<Execution[^>]*>)[^<]+' || echo "")
fi

canonical_states="READY|ACTIVE|STOPPED|FEED_HOLD|INTERRUPTED|OPTIONAL_STOP|PROGRAM_STOPPED|PROGRAM_COMPLETED"

if [[ "$exec_state" =~ ^($canonical_states)$ ]]; then
    echo -e "${GREEN}✓ PASS${NC} - Execution='$exec_state' (canônico)"
else
    echo -e "${YELLOW}⚠ WARN${NC} - Execution='$exec_state' (não canônico, será normalizado)"
fi

echo ""

# Teste 5: Endpoint /ingest
echo -e "${YELLOW}[5/5]${NC} Testando POST /v1/telemetry/ingest..."

payload='{"machine_id":"TEST-001","timestamp":"2025-11-05T05:20:00Z","rpm":4200,"feed_mm_min":850,"state":"running"}'

ingest_response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/telemetry/ingest" \
    -H "Content-Type: application/json" \
    -H "X-Request-Id: validate-001" \
    -H "X-Contract-Fingerprint: 010191590cf1" \
    -d "$payload" 2>/dev/null || echo -e "\n000")

http_code=$(echo "$ingest_response" | tail -1)

if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - /ingest retornou HTTP $http_code"
else
    echo -e "${RED}✗ FAIL${NC} - /ingest retornou HTTP $http_code"
    echo "Response:"
    echo "$ingest_response" | head -n -1
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "${GREEN}✓ VALIDAÇÃO COMPLETA${NC}"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Próximos passos:"
echo "  1. Rodar soak test 5 min:  DURATION_MIN=5  python3 backend/mtconnect_adapter.py"
echo "  2. Rodar soak test 30 min: DURATION_MIN=30 python3 backend/mtconnect_adapter.py"
echo "  3. Campo: trocar AGENT_URL para IP real (http://192.168.1.XXX:5000)"
echo ""
