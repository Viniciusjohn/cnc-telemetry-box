# F2 Adapter — Quick Start

## 🎯 Objetivo

Validar ingestão contínua de dados MTConnect por 30 minutos com:
- ✅ p95 atraso ≤2s
- ✅ jitter p95 <400ms
- ✅ perda <0.5%
- ✅ RPM/Feed coerentes
- ✅ Estados MTConnect normalizados

## ✨ Novidades (Patch de Campo)

### 4 Ajustes Aplicados:
1. ✅ **RotaryVelocity** (não SpindleSpeed deprecated)
2. ✅ **PathFeedrate** com conversão mm/s → mm/min
3. ✅ **Execution** normalizado (READY/ACTIVE → idle/running/stopped)
4. ✅ **/sample** com sequência (não apenas /current)

**Ferramentas disponíveis:**
- `mtconnect_adapter.py` — Adapter Python robusto (produção)
- `mtconnect_ingest_sample.sh` — Script bash com /sample
- `mtconnect_simulator.py` — Simulador com endpoints /probe, /current, /sample

📄 **Ver:** `docs/MTConnect_COMPLIANCE.md` para detalhes técnicos

---

## 🧪 Testes Locais (Sem Agente Real)

### 1. Iniciar Simulador MTConnect

```bash
cd /home/viniciusjohn/iot

# Terminal 1: Backend (porta 8001)
cd backend
source .venv/bin/activate
uvicorn app:app --port 8001 --reload

# Terminal 2: Simulador MTConnect (porta 5000)
python3 scripts/mtconnect_simulator.py --port 5000
```

### 2. Verificar Simulador

```bash
# Probe (estrutura do dispositivo)
curl http://localhost:5000/probe

# Current (valores atuais)
curl http://localhost:5000/current
```

**Saída esperada:** XML MTConnect com `RotaryVelocity`, `PathFeedrate`, `Execution`

### 3. Teste Rápido (30s - Adapter Python)

**Opção A: Adapter Python (recomendado para produção)**

```bash
cd backend
source .venv/bin/activate

export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=0.5  # 30 segundos

python3 mtconnect_adapter.py
```

**Opção B: Script Bash (debugging)**

```bash
export AGENT_IP=localhost
export AGENT_PORT=5000
export API_BASE=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=1

# Script antigo (/current)
./scripts/mtconnect_ingest_test.sh

# OU script novo (/sample com sequência)
./scripts/mtconnect_ingest_sample.sh
```

**Saída esperada:**
```
✅ [timestamp] #1 | RPM=4123.5 Feed=1245.6 State=running | 45ms
✅ [timestamp] #2 | RPM=4089.2 Feed=1198.3 State=running | 38ms
...
📊 Relatório de Ingestão (1 min)
   Amostras esperadas: 30
   Amostras enviadas: 30
   Erros: 0
   Perda: 0.00%
✅ PASS: Perda <0.5%
```

### 4. Teste Completo (30 min)

```bash
export DURATION_MIN=30
./scripts/mtconnect_ingest_test.sh
```

---

## 🏭 Testes com Agente Real (Campo)

### Pré-requisitos

1. **Confirmar com Nestor:**
   - Série da máquina: M70 / M700 / M80?
   - IP da máquina CNC: `192.168.1.XXX`
   - MTConnect Agent rodando? Porta?

2. **Descobrir agente na rede:**

```bash
# Scan de portas MTConnect (5000-5010)
nmap -p 5000-5010 192.168.1.0/24

# Testar conectividade
curl -s http://192.168.1.100:5000/probe | head -50
```

### Executar Teste de Campo

```bash
export AGENT_IP=192.168.1.100  # IP real da máquina
export AGENT_PORT=5000
export API_BASE=http://localhost:8001
export MACHINE_ID=ABR-850
export DURATION_MIN=30

./scripts/mtconnect_ingest_test.sh
```

---

## 📊 Métricas de Aceite

### Latência
- **p50 (mediana):** ≤500ms
- **p95:** ≤2s
- **p99:** ≤5s

### Jitter
- **p95:** <400ms (variação entre requests consecutivos)

### Disponibilidade
- **Perda de amostras:** <0.5% em 30 min
- **Timeout rate:** <1%

### Coerência de Dados
- **RPM:** 0 a 30.000 (sem outliers >50k)
- **Feed:** 0 a 10.000 mm/min (sem outliers >20k)
- **Estados:** Apenas vocabulário MTConnect (ACTIVE, READY, STOPPED, FEED_HOLD, INTERRUPTED)

---

## 🔧 Troubleshooting

### Simulador não inicia

```bash
# Verificar porta 5000 livre
lsof -i :5000

# Usar porta alternativa
python3 scripts/mtconnect_simulator.py --port 5001
```

### Teste falha com "Erro ao buscar MTConnect"

```bash
# Verificar conectividade
curl -v http://localhost:5000/current

# Verificar logs do simulador
# (deve mostrar GET /current 200 OK)
```

### HTTP 422 (Validation Error)

```bash
# Verificar payload enviado
# RPM fora de range (0-30000)?
# Feed fora de range (0-10000)?
# State não é "running"|"stopped"|"idle"?

# Ver logs do backend
# uvicorn mostrará detalhes do erro Pydantic
```

### Perda >0.5%

**Causas possíveis:**
- Rede instável (verificar ping)
- Backend lento (verificar CPU/memória)
- Intervalo muito curto (aumentar de 2s para 3s)

**Mitigação:**
```bash
# Aumentar intervalo (editar script)
INTERVAL_SEC=3

# Rodar novamente
./scripts/mtconnect_ingest_test.sh
```

---

## 📝 Checklist de Aceite F2

- [ ] Teste local (simulador) por 1 min: PASS
- [ ] Teste local (simulador) por 30 min: PASS, perda <0.5%
- [ ] Descobrir agente MTConnect no campo (IP/porta)
- [ ] Validar `/probe` retorna DataItems esperados
- [ ] Teste campo por 5 min: PASS
- [ ] Teste campo por 30 min: PASS, p95 ≤2s, perda <0.5%
- [ ] Documentar estados desconhecidos (se houver)
- [ ] Implementar normalização de unidades (mm/s → mm/min)
- [ ] Implementar normalização de estados (aliases)

---

## 🚀 Próximos Passos

1. **Agora:** Rodar teste local (1 min) com simulador
2. **Hoje:** Confirmar série/IP com Nestor
3. **Amanhã:** Teste de campo (30 min)
4. **F3:** Dashboard PWA consumindo dados reais

---

**Status Atual:** Infraestrutura pronta para testes. Aguardando dados do campo.
