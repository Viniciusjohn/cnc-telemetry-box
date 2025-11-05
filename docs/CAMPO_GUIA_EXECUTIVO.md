# Guia Executivo de Campo — F2 Adapter MTConnect

**Data:** 2025-11-05  
**Objetivo:** Validar 30 min de ingestão contínua com p95 ≤2s, perda <0.5%

---

## 📋 Pré-requisitos (Nestor)

### Informações Necessárias

- [ ] **Série da máquina:** M70 / M700 / M80 / M800?
- [ ] **IP da máquina CNC:** `192.168.1.___`
- [ ] **MTConnect Agent rodando?** Sim / Não
- [ ] **Porta do Agent:** Default 5000 (ou outra?)
- [ ] **Janela de testes:** ≥2h sem interromper produção

### Se MTConnect Agent NÃO está rodando

**Opção A (recomendada):** Instalar **Mitsubishi MTConnect Data Collector**
- Produto: MTConnect Data Collector via Edgecross
- Plataforma: Windows (edge PC ou IPC)
- Licença: Verificar com Mitsubishi/integrador
- Manual: https://www.mitsubishielectric.com/fa/products/cnc/

**Opção B:** Usar SDK Mitsubishi direto (proprietário, mais complexo)

---

## 🔍 PASSO 1: Descobrir Agent (5 min)

### 1.1 Scan de Rede

```bash
# Trocar subnet conforme rede do cliente
nmap -p 5000-5010 192.168.1.0/24
```

**Saída esperada:**
```
Nmap scan report for 192.168.1.100
PORT     STATE SERVICE
5000/tcp open  upnp
```

### 1.2 Testar Probe

```bash
# Trocar IP pelo encontrado no scan
export AGENT_IP=192.168.1.100
export AGENT_PORT=5000

curl -s http://$AGENT_IP:$AGENT_PORT/probe | head -50
```

**Saída esperada:** XML MTConnect com `<MTConnectDevices>`, `<Device>`, `<DataItem type="ROTARY_VELOCITY">`, etc.

**✅ PASS:** XML válido retornado  
**❌ FAIL:** Timeout ou erro → Agent não está rodando (instalar Data Collector)

### 1.3 Validação Completa

```bash
cd /home/viniciusjohn/iot

export AGENT_URL=http://$AGENT_IP:$AGENT_PORT
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

---

## 🧪 PASSO 2: Soak Test Local (5 min → 30 min)

### 2.1 Teste Rápido (5 min)

**Terminal 1: Backend**
```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate
uvicorn app:app --port 8001 --reload
```

**Terminal 2: Adapter (5 min)**
```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate

export AGENT_URL=http://localhost:5000
export API_URL=http://localhost:8001
export MACHINE_ID=CNC-SIM-001
export DURATION_MIN=5

python3 mtconnect_adapter.py
```

**Terminal 3: Simulador (apenas se não tiver Agent real)**
```bash
python3 scripts/mtconnect_simulator.py --port 5000
```

**Saída esperada:**
```
🚀 Adapter iniciado: http://localhost:5000 → http://localhost:8001
✅ #1 | RPM=4123.5 Feed=1245.6 State=running Seq=12345
✅ #2 | RPM=4089.2 Feed=1198.3 State=running Seq=12346
...
✅ #150 | RPM=4200.1 Feed=1190.8 State=running Seq=12495

📊 Relatório Final
   Duração: 300s
   Amostras enviadas: 150
   Erros: 0
   Perda: 0.00%
```

**✅ PASS:** Perda <0.5%, sem erros  
**❌ FAIL:** Perda ≥0.5% ou muitos erros → investigar (rede? agent? backend?)

### 2.2 Teste Completo (30 min)

```bash
export DURATION_MIN=30
python3 mtconnect_adapter.py
```

**Critérios de aceite:**
- ✅ Amostras esperadas: ~900 (30min ÷ 2s)
- ✅ Perda: <0.5% (~4 amostras ou menos)
- ✅ Erros: 0
- ✅ p95 latência: ≤2s (verificar logs)

---

## 🏭 PASSO 3: Campo com Agent Real (30 min)

### 3.1 Configurar Variáveis

```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate

# Trocar IP pelo descoberto no PASSO 1
export AGENT_URL=http://192.168.1.100:5000
export API_URL=http://localhost:8001
export MACHINE_ID=ABR-850  # Trocar pelo ID real
export DURATION_MIN=30
export POLL_INTERVAL=2.0
```

### 3.2 Executar Adapter

```bash
python3 mtconnect_adapter.py 2>&1 | tee soak_test_campo_$(date +%Y%m%d_%H%M%S).log
```

**Comando acima:**
- Roda adapter por 30 min
- Salva log completo em arquivo timestampado
- Mostra output em tempo real

### 3.3 Monitorar Execução

**Abrir outro terminal para monitorar:**

```bash
# Ver últimas 20 linhas do log
tail -f soak_test_campo_*.log

# Contar amostras enviadas
grep "✅" soak_test_campo_*.log | wc -l

# Contar erros
grep "ERROR" soak_test_campo_*.log | wc -l
```

### 3.4 Validar Coerência com Painel Físico

**Durante o teste:**
1. Anotar valores do painel CNC (RPM, Feed):
   - Exemplo: Painel mostra `RPM=4200, Feed=1200 mm/min`

2. Comparar com log do adapter:
   ```bash
   grep "RPM=42" soak_test_campo_*.log | tail -5
   ```

3. Verificar margem de ±1%:
   - `RPM=4200 ±42` → 4158-4242 (ok)
   - `Feed=1200 ±12` → 1188-1212 (ok)

**✅ PASS:** Valores dentro de ±1%  
**❌ FAIL:** Divergência >1% → verificar mapeamento de DataItems

---

## 📊 PASSO 4: Análise de Resultados

### 4.1 Relatório Automático

Ao final dos 30 min, o adapter exibe:

```
📊 Relatório Final
   Duração: 1800s
   Amostras enviadas: 897
   Erros: 2
   Perda: 0.33%
```

**Critérios:**
- ✅ Perda <0.5%: **PASS**
- ❌ Perda ≥0.5%: **FAIL** (investigar)

### 4.2 Análise de Latência

```bash
# Extrair latências do log (se estiver logando)
grep "latency" soak_test_campo_*.log | awk '{print $NF}' | sort -n | tail -10

# Calcular p95 (95% das amostras)
# Usar script Python ou online calculator
```

**Critério:**
- ✅ p95 ≤2000ms: **PASS**
- ❌ p95 >2000ms: **FAIL** (rede lenta? agent sobrecarregado?)

### 4.3 Estados Desconhecidos

```bash
# Buscar warnings de estados não-canônicos
grep "Estado desconhecido" soak_test_campo_*.log
```

**Se encontrar:**
- Adicionar mapeamento em `EXECUTION_MAP` (backend/mtconnect_adapter.py)
- Exemplo: `"PAUSED_BY_OPERATOR": "stopped"`

---

## ✅ Checklist de Aceite F2

### Pré-campo
- [ ] Confirmar série/IP com Nestor
- [ ] Scan de rede encontrou Agent (porta 5000)
- [ ] `/probe` retorna XML MTConnect válido
- [ ] DataItems presentes: RotaryVelocity, PathFeedrate, Execution
- [ ] Validação `validate_f2.sh` passou (5/5 testes)

### Testes Locais
- [ ] Soak 5 min (simulador): perda <0.5%
- [ ] Soak 30 min (simulador): perda <0.5%, sem erros

### Campo
- [ ] Soak 5 min (agent real): perda <0.5%
- [ ] Soak 30 min (agent real): perda <0.5%, p95 ≤2s
- [ ] Coerência RPM/Feed com painel físico (±1%)
- [ ] Log salvo: `soak_test_campo_YYYYMMDD_HHMMSS.log`
- [ ] Sem estados desconhecidos (ou todos mapeados)

### Entregáveis
- [ ] Relatório final salvo
- [ ] Screenshots do painel CNC vs log do adapter
- [ ] Confirmação do Nestor: dados coerentes

---

## 🚨 Troubleshooting

### Problema: Agent não responde (timeout)

**Causas:**
- Agent não está rodando
- Firewall bloqueando porta 5000
- IP/porta errados

**Solução:**
```bash
# Testar conectividade básica
ping 192.168.1.100

# Testar porta
telnet 192.168.1.100 5000

# Verificar firewall (se tiver acesso ao servidor)
sudo ufw status
```

### Problema: Perda >0.5%

**Causas:**
- Rede instável (verificar ping)
- Backend lento (verificar CPU/memória)
- Agent sobrecarregado

**Solução:**
```bash
# Aumentar intervalo de 2s para 3s
export POLL_INTERVAL=3.0

# Reduzir count de 200 para 100
# (editar mtconnect_adapter.py linha 85)
```

### Problema: RPM/Feed divergem do painel (>1%)

**Causas:**
- DataItem errado (SpindleOverride vs RotaryVelocity)
- Unidades erradas (mm/s não convertidas)
- Mapeamento incorreto no probe

**Solução:**
```bash
# Ver probe completo
curl -s http://$AGENT_IP:5000/probe | xmllint --format -

# Verificar DataItems:
# - type="ROTARY_VELOCITY" units="REVOLUTION/MINUTE"
# - type="PATH_FEEDRATE" units="MILLIMETER/SECOND"
```

### Problema: Estados desconhecidos

**Exemplo:**
```
⚠️ Estado desconhecido: PAUSED_BY_OPERATOR (mapeado para idle)
```

**Solução:**
Adicionar em `backend/mtconnect_adapter.py`:
```python
EXECUTION_MAP = {
    # ... existentes
    "PAUSED_BY_OPERATOR": "stopped",  # Adicionar
}
```

---

## 🎯 Após Aceite de F2

### Próximas Fases

**F3 — Dashboard com Dados Reais**
- Conectar frontend ao backend
- Polling 2s do endpoint `/v1/machines/ABR-850/status`
- Validar PWA instalável no mobile do Nestor
- Lighthouse ≥90

**F4 — Piloto 30 min com Nestor**
- Lado a lado: painel CNC vs dashboard PWA
- Atraso p95 ≤2s (user-perceived)
- Disponibilidade ≥99%
- Aceitação formal

---

## 📞 Contatos e Referências

### Nestor (Cliente)
- Confirmar série/IP
- Agendar janela de testes (≥2h)
- Validar dados lado a lado

### Mitsubishi/Integrador
- Licença do MTConnect Data Collector
- Instalação do Edgecross
- Suporte técnico

### Referências Técnicas
- **MTConnect Standard:** https://www.mtconnect.org/documents
- **Mitsubishi MTConnect:** https://www.mitsubishielectric.com/fa/products/cnc/
- **Documentação interna:** `docs/MTConnect_COMPLIANCE.md`

---

## 📄 Templates de Relatório

### Email para Nestor (Pré-teste)

```
Assunto: Teste de Telemetria CNC — Agendamento

Olá Nestor,

Para validar a integração de telemetria da máquina ABR-850, precisamos:

1. Série da máquina: M70 / M700 / M80? (verificar painel)
2. IP da máquina CNC: 192.168.1.___
3. Confirmar se há MTConnect Agent rodando (porta 5000)
4. Janela de ≥2h para testes sem interromper produção

Data sugerida: [DATA]
Horário: [HORÁRIO]

Iremos rodar teste de 30 min com monitoramento contínuo de RPM/Feed.

Att,
[SEU NOME]
```

### Email para Nestor (Pós-teste - PASS)

```
Assunto: ✅ Teste de Telemetria — Aprovado

Olá Nestor,

Teste de 30 min concluído com sucesso:

📊 Resultados:
- Amostras coletadas: 897/900 (99.67%)
- Perda: 0.33% ✓
- Erros: 0 ✓
- Coerência RPM/Feed: ±0.8% ✓

Próximo passo: Dashboard PWA (F3) para visualização em tempo real.

Anexo: soak_test_campo_20251105_021900.log

Att,
[SEU NOME]
```

---

**Última atualização:** 2025-11-05 02:19 UTC-03:00
