#!/usr/bin/env bash
# Smoke tests automatizados para F3
# Valida headers, contrato JSON, CORS, MTConnect e UI

set -euo pipefail

API_URL="${API_URL:-http://localhost:8001}"
AGENT_URL="${AGENT_URL:-http://localhost:5000}"
MACHINE_ID="${MACHINE_ID:-CNC-SIM-001}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 F3 Smoke Tests"
echo "════════════════════════════════════════"
echo "API: $API_URL"
echo "Agent: $AGENT_URL"
echo "Machine: $MACHINE_ID"
echo ""

PASS=0
FAIL=0

function test_pass() {
    echo -e "${GREEN}✅ PASS${NC} - $1"
    ((PASS++))
}

function test_fail() {
    echo -e "${RED}❌ FAIL${NC} - $1"
    ((FAIL++))
}

function test_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC} - $1"
}

# Test 1: Headers canônicos
echo "1️⃣  Testando headers canônicos..."
HEADERS=$(curl -sI "$API_URL/v1/machines/$MACHINE_ID/status" 2>/dev/null || echo "")

if echo "$HEADERS" | grep -qi "cache-control: no-store"; then
    test_pass "Cache-Control: no-store presente"
else
    test_fail "Cache-Control: no-store ausente"
fi

if echo "$HEADERS" | grep -qi "vary:"; then
    test_pass "Vary presente"
else
    test_fail "Vary ausente"
fi

if echo "$HEADERS" | grep -qi "x-contract-fingerprint:"; then
    test_pass "X-Contract-Fingerprint presente"
else
    test_fail "X-Contract-Fingerprint ausente"
fi

if echo "$HEADERS" | grep -qi "server-timing:"; then
    test_pass "Server-Timing presente"
else
    test_fail "Server-Timing ausente"
fi

echo ""

# Test 2: Contrato JSON
echo "2️⃣  Testando contrato JSON..."
JSON=$(curl -s "$API_URL/v1/machines/$MACHINE_ID/status" 2>/dev/null || echo "{}")

if echo "$JSON" | jq -e '.rpm >= 0' >/dev/null 2>&1; then
    test_pass "Campo 'rpm' válido (≥0)"
else
    test_fail "Campo 'rpm' inválido ou ausente"
fi

if echo "$JSON" | jq -e '.feed_mm_min >= 0' >/dev/null 2>&1; then
    test_pass "Campo 'feed_mm_min' válido (≥0)"
else
    test_fail "Campo 'feed_mm_min' inválido ou ausente"
fi

if echo "$JSON" | jq -e '.state | IN("running","stopped","idle")' >/dev/null 2>&1; then
    test_pass "Campo 'state' normalizado"
else
    test_fail "Campo 'state' inválido"
fi

if echo "$JSON" | jq -e '.updated_at' >/dev/null 2>&1; then
    test_pass "Campo 'updated_at' presente"
else
    test_fail "Campo 'updated_at' ausente"
fi

echo ""

# Test 3: Preflight 204
echo "3️⃣  Testando preflight CORS (OPTIONS)..."
PREFLIGHT=$(curl -s -X OPTIONS "$API_URL/v1/machines/$MACHINE_ID/status" \
    -H "Origin: http://localhost:5173" \
    -H "Access-Control-Request-Method: GET" \
    -D - 2>/dev/null || echo "")

if echo "$PREFLIGHT" | grep -q "HTTP/1.1 204"; then
    test_pass "Preflight retorna 204 No Content"
else
    test_fail "Preflight não retorna 204"
fi

if echo "$PREFLIGHT" | grep -qi "access-control-allow-origin:"; then
    test_pass "CORS allow-origin presente"
else
    test_fail "CORS allow-origin ausente"
fi

echo ""

# Test 4: MTConnect /current
echo "4️⃣  Testando MTConnect /current..."
CURRENT=$(curl -s "$AGENT_URL/current" 2>/dev/null || echo "")

if echo "$CURRENT" | grep -q "MTConnectStreams"; then
    test_pass "MTConnect /current responde"
else
    test_fail "MTConnect /current não responde"
fi

if echo "$CURRENT" | grep -q "RotaryVelocity"; then
    test_pass "RotaryVelocity presente"
else
    test_warn "RotaryVelocity ausente (pode estar usando SpindleSpeed)"
fi

if echo "$CURRENT" | grep -q "PathFeedrate"; then
    test_pass "PathFeedrate presente"
else
    test_fail "PathFeedrate ausente"
fi

if echo "$CURRENT" | grep -q "Execution"; then
    test_pass "Execution presente"
else
    test_fail "Execution ausente"
fi

echo ""

# Test 5: MTConnect /sample (sequência)
echo "5️⃣  Testando MTConnect /sample (sequência)..."
SAMPLE=$(curl -s "$AGENT_URL/sample?count=3" 2>/dev/null || echo "")

if echo "$SAMPLE" | grep -q "nextSequence"; then
    test_pass "nextSequence presente no Header"
    NEXT_SEQ=$(echo "$SAMPLE" | xmllint --format - | grep -oP 'nextSequence="\K[0-9]+' | head -1)
    echo "   nextSequence: $NEXT_SEQ"
else
    test_fail "nextSequence ausente no Header"
fi

if echo "$SAMPLE" | grep -q "sequence="; then
    test_pass "Amostras com 'sequence' presente"
else
    test_fail "Amostras sem 'sequence'"
fi

echo ""

# Test 6: Unidades
echo "6️⃣  Validando unidades..."
UNITS=$(curl -s "$AGENT_URL/current" 2>/dev/null | xmllint --format - | grep -E "PathFeedrate.*units" || echo "")

if echo "$UNITS" | grep -q 'units="MILLIMETER/SECOND"'; then
    test_pass "PathFeedrate em MILLIMETER/SECOND (correto)"
elif echo "$UNITS" | grep -q 'units="MILLIMETER/MINUTE"'; then
    test_warn "PathFeedrate em MILLIMETER/MINUTE (adapter não precisa converter)"
else
    test_fail "PathFeedrate com unidade desconhecida"
fi

echo ""

# Resumo
echo "════════════════════════════════════════"
echo "📊 RESUMO"
echo "════════════════════════════════════════"
echo -e "${GREEN}✅ PASS: $PASS${NC}"
echo -e "${RED}❌ FAIL: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 Todos os testes passaram!${NC}"
    echo ""
    echo "Próximos passos:"
    echo "1. Validar UI no navegador (http://localhost:5173)"
    echo "2. Executar Playwright: cd frontend && npx playwright test"
    echo "3. Preencher docs/F3_VALIDACAO.md"
    echo "4. Anexar relatório na issue #4"
    exit 0
else
    echo -e "${RED}❌ Alguns testes falharam. Verificar logs acima.${NC}"
    exit 1
fi
