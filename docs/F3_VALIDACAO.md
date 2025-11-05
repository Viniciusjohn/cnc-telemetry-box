# F3 — Relatório de Validação (Smoke Tests)

**Data:** 2025-11-05  
**Ambiente:** Desenvolvimento local (localhost)

---

## ✅ Checklist de Validação

| # | Teste | Status | Observação |
|---|-------|--------|------------|
| 1 | Headers canônicos | ⏳ | Cache-Control, Vary, Fingerprint, Server-Timing |
| 2 | Contrato JSON | ⏳ | Schema válido (rpm, feed_mm_min, state, updated_at) |
| 3 | Preflight 204 | ⏳ | OPTIONS sem corpo, CORS correto |
| 4 | MTConnect /current | ⏳ | RotaryVelocity, PathFeedrate, Execution |
| 5 | MTConnect /sample | ⏳ | nextSequence, sequência monótona |
| 6 | Unidades corretas | ⏳ | mm/s → mm/min (×60), ACTIVE → running |
| 7 | UI Dashboard | ⏳ | 4 cards, polling 2s, cores por estado |
| 8 | Playwright E2E | ⏳ | 4 testes passando |

---

## 📋 Comandos Executados

### 1. Headers Canônicos

```bash
curl -sI http://localhost:8001/v1/machines/CNC-SIM-001/status | \
  grep -Ei 'cache-control|vary|server-timing|x-contract-fingerprint'
```

**Resultado:**
```
# Colar saída aqui após execução
```

---

### 2. Contrato JSON

```bash
curl -s http://localhost:8001/v1/machines/CNC-SIM-001/status | \
  jq -e '.rpm>=0 and .feed_mm_min>=0 and (.state|IN("running","stopped","idle"))'
```

**Resultado:**
```json
# Colar saída aqui
```

---

### 3. Preflight 204

```bash
curl -s -X OPTIONS http://localhost:8001/v1/machines/CNC-SIM-001/status \
  -H "Origin: http://localhost:5173" -D -
```

**Resultado:**
```
# Colar saída aqui
```

---

### 4. MTConnect /current

```bash
curl -s http://localhost:5000/current | xmllint --format - | head -n 30
```

**Resultado:**
```xml
<!-- Colar saída aqui -->
```

---

### 5. MTConnect /sample

```bash
curl -s "http://localhost:5000/sample?count=5" | xmllint --format - | sed -n '1,60p'
```

**Resultado:**
```xml
<!-- Colar saída aqui -->
```

---

### 6. Unidades e Estados

```bash
curl -s http://localhost:5000/current | xmllint --format - | \
  grep -E "PathFeedrate|units|RotaryVelocity|Execution"
```

**Resultado:**
```
# Colar saída aqui
```

**Validação de conversão:**
- PathFeedrate no XML: ____ mm/s
- PathFeedrate no /status: ____ mm/min
- Conversão correta (×60): ✅/❌

---

### 7. UI Dashboard

**URL:** http://localhost:5173

**Screenshot Desktop:**
```
[Anexar screenshot]
```

**Screenshot Mobile:**
```
[Anexar screenshot]
```

**Observações:**
- Cards visíveis: ✅/❌
- Polling funcional: ✅/❌
- Cores corretas: ✅/❌
- Console sem erros: ✅/❌

---

### 8. Playwright E2E

```bash
cd frontend
npx playwright test e2e/status.spec.ts --reporter=list
```

**Resultado:**
```
# Colar saída aqui
```

---

## 🎯 Critérios de Aceite F3

| Critério | Meta | Resultado | Status |
|----------|------|-----------|--------|
| **Headers canônicos** | 4/4 presentes | TBD | ⏳ |
| **Schema JSON** | Válido | TBD | ⏳ |
| **Preflight 204** | Sem corpo | TBD | ⏳ |
| **MTConnect válido** | RotaryVelocity+PathFeedrate | TBD | ⏳ |
| **Conversão ×60** | Correta | TBD | ⏳ |
| **UI funcional** | Polling 2s | TBD | ⏳ |
| **Playwright** | 4/4 PASS | TBD | ⏳ |

---

## 📊 Resultado Final

**Status:** ⏳ AGUARDANDO EXECUÇÃO

**Próximos Passos:**
1. Preencher este relatório após execução dos testes
2. Anexar na issue #4
3. Se PASS, avançar para F4 (campo)

---

**Assinatura:** _______________________  
**Data:** _______________________
