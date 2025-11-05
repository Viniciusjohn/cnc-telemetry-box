# F4 Piloto de Campo — Planejamento

**Status:** 📝 PLANEJAMENTO (NÃO EXECUTADO)  
**Objetivo:** Validar sistema completo em campo com Novatech (Mitsubishi) por ≥30 min

---

## 🎯 Escopo

### 1. Adapter Resiliente (Persistência de Estado)
- ✅ Persistir `instanceId`, `lastSequence`, `lastSeenAt` em `backend/state/mtc_markers.json`
- ✅ Detectar mudança de `instanceId` (Agent reiniciou)
- ✅ Retomar de `lastSequence` ou iniciar fresh se necessário
- ✅ Logging detalhado de recuperação

### 2. Scripts Operacionais
- ✅ `scripts/discover_agent.sh` — Descobrir Agent na rede
- ✅ `scripts/field_soak_30m.sh` — Soak test automatizado
- ✅ `scripts/attach_report.sh` — Anexar relatório na issue #5

### 3. Documentação de Campo
- ✅ `docs/F4_RELATORIO_CAMPO.md` — Template de relatório
- ✅ `docs/email_novatech.md` — Template de email

### 4. Validações
- ✅ Sequência MTConnect sem gaps
- ✅ Headers canônicos em /status
- ✅ UI atualizando a cada 2s
- ✅ Playwright E2E

---

## 📁 Arquivos a Criar/Modificar

### 1. `backend/state/mtc_markers.json` (NOVO - gitignored)

```json
{
  "machine_id": "ABR-850",
  "instanceId": "12345678",
  "lastSequence": 229793,
  "lastSeenAt": "2025-11-05T06:00:00Z"
}
```

### 2. `backend/.gitignore` (ADICIONAR)

```
state/
*.log
```

### 3. `backend/mtconnect_adapter.py` (MODIFICAR - Adicionar Persistência)

**Adicionar após imports:**
```python
import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state" / "mtc_markers.json"

def load_state(machine_id: str) -> dict:
    """Carrega estado persistido ou retorna default"""
    if not STATE_FILE.exists():
        return {"machine_id": machine_id, "instanceId": None, "lastSequence": None, "lastSeenAt": None}
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(machine_id: str, instance_id: str, last_seq: int):
    """Salva estado para retomada"""
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({
            "machine_id": machine_id,
            "instanceId": instance_id,
            "lastSequence": last_seq,
            "lastSeenAt": datetime.now(timezone.utc).isoformat()
        }, f, indent=2)
```

**Na função `run()`, após descoberta:**
```python
# Carregar estado anterior
prev_state = load_state(machine_id)
logger.info(f"Estado anterior: instanceId={prev_state.get('instanceId')}, lastSeq={prev_state.get('lastSequence')}")

# Detectar mudança de instanceId
if prev_state.get("instanceId") and prev_state["instanceId"] != instance_id:
    logger.warning(f"⚠️ instanceId mudou ({prev_state['instanceId']} → {instance_id}). Agent reiniciou!")
    logger.info("Iniciando fresh com /current para capturar nextSequence")
    next_seq = None  # Forçar início pelo /current
else:
    next_seq = prev_state.get("lastSequence")
    if next_seq:
        logger.info(f"↪️ Retomando de lastSequence={next_seq}")

# ... (resto do loop)

# Ao final de cada iteração bem-sucedida:
save_state(machine_id, instance_id, next_seq)
```

---

### 4. `scripts/discover_agent.sh` (NOVO)

```bash
#!/usr/bin/env bash
# Descobrir MTConnect Agent na rede

set -euo pipefail

NETWORK="${1:-192.168.1.0/24}"
PORTS="5000-5010"

echo "🔍 Descobrindo MTConnect Agent em $NETWORK (portas $PORTS)..."

nmap -p "$PORTS" "$NETWORK" | grep -B 4 "open" || echo "Nenhum Agent encontrado"

echo ""
echo "Testando /probe em IPs detectados..."

for ip in $(nmap -p "$PORTS" "$NETWORK" -oG - | grep "open" | awk '{print $2}'); do
    for port in $(seq 5000 5010); do
        url="http://$ip:$port/probe"
        echo "Tentando $url..."
        if curl -s -m 2 "$url" | grep -q "MTConnectDevices"; then
            echo "✅ Agent encontrado: $url"
            echo ""
            curl -s "$url" | xmllint --format - | head -20
            exit 0
        fi
    done
done

echo "❌ Nenhum Agent MTConnect encontrado"
exit 1
```

---

### 5. `scripts/field_soak_30m.sh` (NOVO)

```bash
#!/usr/bin/env bash
# Soak test de campo automatizado

set -euo pipefail

AGENT_URL="${AGENT_URL:-http://192.168.1.100:5000}"
API_URL="${API_URL:-http://localhost:8001}"
MACHINE_ID="${MACHINE_ID:-ABR-850}"
DURATION_MIN="${DURATION_MIN:-30}"

LOG_FILE="soak_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 Iniciando soak test de campo"
echo "   Agent: $AGENT_URL"
echo "   API: $API_URL"
echo "   Máquina: $MACHINE_ID"
echo "   Duração: ${DURATION_MIN} min"
echo "   Log: $LOG_FILE"
echo ""

cd "$(dirname "$0")/../backend"
source .venv/bin/activate

python3 mtconnect_adapter.py 2>&1 | tee "../$LOG_FILE"

echo ""
echo "📊 Gerando resumo..."

SAMPLES=$(grep -c "✅ #" "../$LOG_FILE" || echo 0)
ERRORS=$(grep -c "❌" "../$LOG_FILE" || echo 0)

echo ""
echo "════════════════════════════════════════"
echo "  RESUMO DO SOAK TEST"
echo "════════════════════════════════════════"
echo "Duração: ${DURATION_MIN} min"
echo "Amostras enviadas: $SAMPLES"
echo "Erros: $ERRORS"
echo "Log salvo em: $LOG_FILE"
echo ""

if [ "$ERRORS" -eq 0 ] && [ "$SAMPLES" -gt $((DURATION_MIN * 25)) ]; then
    echo "✅ PASS - Soak test bem-sucedido!"
    exit 0
else
    echo "❌ FAIL - Verificar log para detalhes"
    exit 1
fi
```

---

### 6. `scripts/attach_report.sh` (NOVO)

```bash
#!/usr/bin/env bash
# Anexar relatório na issue #5

set -euo pipefail

REPORT_FILE="${1:-docs/F4_RELATORIO_CAMPO.md}"
ISSUE_NUMBER="5"
REPO="Viniciusjohn/cnc-telemetry"

if [ ! -f "$REPORT_FILE" ]; then
    echo "❌ Relatório não encontrado: $REPORT_FILE"
    exit 1
fi

echo "📎 Anexando relatório na issue #$ISSUE_NUMBER..."

gh issue comment "$ISSUE_NUMBER" -R "$REPO" --body-file "$REPORT_FILE"

echo "✅ Relatório anexado com sucesso!"
echo "   https://github.com/$REPO/issues/$ISSUE_NUMBER"
```

---

### 7. `docs/F4_RELATORIO_CAMPO.md` (TEMPLATE)

```markdown
# F4 — Relatório de Piloto de Campo

**Data:** YYYY-MM-DD  
**Local:** Novatech (Mitsubishi/Valfenger)  
**Responsável:** [Nome]

---

## 📊 Informações da Máquina

| Campo | Valor |
|-------|-------|
| **Série** | M70/M700/M80/M800 |
| **IP** | 192.168.1.XXX |
| **Porta Agent** | 5000 |
| **Machine ID** | ABR-850 |

---

## 🧪 Configuração do Teste

| Parâmetro | Valor |
|-----------|-------|
| **Duração** | 30 min |
| **Poll interval** | 2s |
| **Endpoint** | /sample |
| **Sequência inicial** | XXXXX |
| **Sequência final** | YYYYY |

---

## 📈 Resultados

| Métrica | Meta | Resultado | Status |
|---------|------|-----------|--------|
| **Amostras esperadas** | ~900 | TBD | ⏳ |
| **Amostras enviadas** | ~900 | TBD | ⏳ |
| **Erros** | 0 | TBD | ⏳ |
| **Perda** | <0.5% | TBD% | ⏳ |
| **p95 atraso** | ≤2s | TBD s | ⏳ |

---

## ✅ Validações MTConnect

- [ ] RotaryVelocity usado (não SpindleSpeed)
- [ ] PathFeedrate convertido mm/s → mm/min
- [ ] Execution normalizado (running|stopped|idle)
- [ ] Sequência monótona sem gaps
- [ ] Headers canônicos presentes

---

## 🖥️ Dashboard (UI)

**Screenshots:**
- Desktop: [anexar]
- Mobile: [anexar]

**Observações:**
- Polling a cada 2s: ✅/❌
- Cores por estado corretas: ✅/❌
- Valores coerentes com painel físico (±1%): ✅/❌

---

## 📝 Observações de Campo

### Pontos Positivos
- TBD

### Problemas Encontrados
- TBD

### Ações Corretivas
- TBD

---

## 🎯 Aceite Final

- [ ] Perda <0.5%
- [ ] Erros = 0
- [ ] Sequência sem gaps
- [ ] UI atualizando
- [ ] Nestor aprovou

---

**Status:** ⏳ AGUARDANDO EXECUÇÃO
```

---

### 8. `docs/email_novatech.md` (TEMPLATE)

```markdown
# Email para Novatech — Agendamento de Piloto F4

**Para:** [Nestor / Contato Técnico]  
**Assunto:** Agendamento de Piloto - Sistema de Telemetria CNC

---

Olá [Nome],

Estamos finalizando a validação do sistema de telemetria CNC e gostaríamos de agendar o piloto de campo na Novatech.

## 📋 Informações Necessárias

Para executar o teste, precisamos confirmar:

1. **Máquina CNC:**
   - Série: M70 / M700 / M80 / M800?
   - Serial / Identificação:

2. **Conectividade:**
   - IP da máquina: `192.168.1.___`
   - MTConnect Agent instalado? Porta?
   - Caso não haja Agent: podemos instalar o **MTConnect Data Collector** (Edgecross)?

3. **Janela de Testes:**
   - Data/hora sugerida:
   - Duração: **≥2 horas** (sem interromper produção)

## 🎯 Objetivo do Piloto

- Validar coleta contínua de dados por 30 minutos
- Confirmar precisão de RPM/Feed (±1% vs painel físico)
- Demonstrar dashboard mobile/desktop atualizando em tempo real

## 📦 Entregáveis

- Relatório técnico com métricas
- Screenshots do dashboard
- Confirmação de aceite

---

Aguardamos retorno para agendarmos.

Atenciosamente,  
[Seu Nome]
```

---

## 🧪 Smoke Tests (Campo)

### 1. Descobrir Agent

```bash
./scripts/discover_agent.sh 192.168.1.0/24
```

**Saída esperada:**
```
✅ Agent encontrado: http://192.168.1.100:5000/probe
<MTConnectDevices>
  <Header instanceId="12345678" .../>
  ...
</MTConnectDevices>
```

---

### 2. Validar Sequência

```bash
export AGENT_URL=http://192.168.1.100:5000

curl -s "$AGENT_URL/sample?count=3" | xmllint --format - | grep -E "nextSequence|sequence="
```

**Saída esperada:**
```
nextSequence="12345"
sequence="12342"
sequence="12343"
sequence="12344"
```

---

### 3. Validar Unidades/Estados

```bash
curl -s "$AGENT_URL/current" | xmllint --format - | grep -E "PathFeedrate|units|RotaryVelocity|Execution"
```

**Saída esperada:**
```xml
<RotaryVelocity ... units="REVOLUTION/MINUTE">4200</RotaryVelocity>
<PathFeedrate ... units="MILLIMETER/SECOND">14.5</PathFeedrate>
<Execution>ACTIVE</Execution>
```

---

### 4. Soak Test 30 Min

```bash
export AGENT_URL=http://192.168.1.100:5000
export MACHINE_ID=ABR-850
export DURATION_MIN=30

./scripts/field_soak_30m.sh
```

---

### 5. Validar Backend

```bash
curl -s http://localhost:8001/v1/machines/ABR-850/status | jq

curl -sI http://localhost:8001/v1/machines/ABR-850/status | \
  grep -Ei 'cache-control|vary|x-contract-fingerprint'
```

---

### 6. Validar UI

```bash
cd frontend
npm run dev &
sleep 5
open http://localhost:5173
```

**Verificar:**
- ✅ Cards aparecem
- ✅ Valores atualizam a cada ~2s
- ✅ Cores corretas (verde/amarelo/vermelho)

---

### 7. Playwright E2E

```bash
cd frontend
npx playwright test e2e/status.spec.ts
```

---

## 🚨 Riscos e Mitigações

### Risco 1: instanceId Muda (Agent Reinicia)

**Sintoma:** Adapter para de funcionar após reboot do Agent

**Mitigação:**
- Persistir `instanceId` em `state/mtc_markers.json`
- Detectar mudança e reiniciar de `/current`
- Logging claro: `⚠️ instanceId mudou, iniciando fresh`

---

### Risco 2: Rede Instável

**Sintoma:** Timeouts frequentes, perda >0.5%

**Mitigação:**
- Retry com exponential backoff
- Aumentar timeout de 5s para 10s
- Buffer local para offline-first (futuro)

---

### Risco 3: Unidades Incorretas

**Sintoma:** Feed exibido errado (10x menor/maior)

**Mitigação:**
- Validar `units="MILLIMETER/SECOND"` no XML
- Converter explicitamente ×60
- Logging: `PathFeedrate: 14.5 mm/s → 870.0 mm/min`

---

## ✅ Gates de Aceite F4

| Gate | Critério | Como Validar |
|------|----------|--------------|
| **G1** | Sequência sem gaps | Analisar log, verificar monotonia |
| **G2** | Perda <0.5% | Relatório final do adapter |
| **G3** | Erros = 0 | grep "❌" no log |
| **G4** | Headers canônicos | curl -I /status |
| **G5** | UI atualizando | Observar timestamp mudando |
| **G6** | Playwright PASS | npx playwright test |
| **G7** | Nestor aprova | Assinatura no relatório |

---

## 📊 Checklist de Execução

### Pré-Campo
- [ ] Confirmar série/IP com Nestor
- [ ] Agendar janela ≥2h
- [ ] Testar discover_agent.sh localmente
- [ ] Revisar F2_RELATORIO_SOAK_30MIN.md

### No Campo
- [ ] Executar discover_agent.sh
- [ ] Validar /probe, /current, /sample
- [ ] Rodar field_soak_30m.sh
- [ ] Capturar screenshots (mobile + desktop)
- [ ] Comparar RPM/Feed com painel físico (±1%)

### Pós-Campo
- [ ] Preencher F4_RELATORIO_CAMPO.md
- [ ] Commit relatório + log
- [ ] ./scripts/attach_report.sh
- [ ] Solicitar aceite do Nestor
- [ ] Fechar issue #5 se PASS

---

## 📁 Estrutura de Arquivos F4

```
/home/viniciusjohn/iot/
├── backend/
│   ├── state/              # NOVO (gitignored)
│   │   └── mtc_markers.json
│   ├── mtconnect_adapter.py  # MODIFICADO (persistência)
│   └── .gitignore          # ADICIONAR state/
├── scripts/
│   ├── discover_agent.sh   # NOVO
│   ├── field_soak_30m.sh   # NOVO
│   └── attach_report.sh    # NOVO
└── docs/
    ├── F4_RELATORIO_CAMPO.md  # TEMPLATE
    └── email_novatech.md      # TEMPLATE
```

---

## 🎯 Próximos Passos

### 1. Implementar (após aprovação)

```bash
# 1. Criar estrutura
mkdir -p backend/state
touch backend/state/.gitkeep
echo "state/" >> backend/.gitignore

# 2. Modificar adapter com persistência
# (ver diffs acima)

# 3. Criar scripts
chmod +x scripts/discover_agent.sh
chmod +x scripts/field_soak_30m.sh
chmod +x scripts/attach_report.sh

# 4. Criar templates
# docs/F4_RELATORIO_CAMPO.md
# docs/email_novatech.md

# 5. Commit
git add backend/ scripts/ docs/
git commit -m "F4: Adapter resiliente + scripts de campo + templates"
git push origin main
```

---

### 2. Enviar Email para Nestor

Usar template `docs/email_novatech.md` para agendar.

---

### 3. Executar no Campo

```bash
# Dia do piloto:
./scripts/discover_agent.sh
export AGENT_URL=http://192.168.1.100:5000
export MACHINE_ID=ABR-850
./scripts/field_soak_30m.sh
```

---

### 4. Anexar Relatório

```bash
./scripts/attach_report.sh docs/F4_RELATORIO_CAMPO.md
```

---

**Status:** 📝 PLANEJAMENTO COMPLETO - PRONTO PARA APROVAÇÃO E IMPLEMENTAÇÃO

**Aprovação:** Aguardando comando "executar F4" ou ajustes
