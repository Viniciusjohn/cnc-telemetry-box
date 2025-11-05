# 🎯 CNC Telemetry — Roadmap Executivo (Revisado)
**Data:** 2025-11-05  
**Versão:** 2.0 (baseado em feedback executivo)  
**Foco:** Valor em 30 dias + Gates objetivos + Métricas OEE/SLA

---

## 🚀 Estratégia: Valor Rápido → Escala Sólida → Enterprise

### Princípios
1. **Valor em 30 dias:** Histórico + Alertas + Multi-máquina (F5-F7)
2. **ML/Edge em Q2'26:** Base sólida antes de complexidade
3. **OEE como âncora:** Métrica universal para ROI
4. **Gates objetivos:** Métricas mensuráveis, não opinião
5. **Conformidade desde cedo:** SOC 2/ISO 27001 trilha definida

---

## �� Horizonte de Execução

### ⚡ Agora → 30 Dias — FUNDAÇÃO SÓLIDA (F5-F7)
**Objetivo:** Travar valor comercial com histórico, alertas proativos e multi-máquina

#### **Gate 5: Histórico 30 Dias (TimescaleDB)**
**Prazo:** Semana 1-2 (7-14 dias)

**Entregas:**
- PostgreSQL 15+ com extensão TimescaleDB
- Hypertable `telemetry` com particionamento temporal
- Retention policy (30 dias automático)
- Continuous aggregates (5min, 1h, 1d)
- Endpoint `/v1/machines/{id}/history?from=X&to=Y&resolution=5m`

**Implementação:**
```sql
-- Schema TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE telemetry (
  ts TIMESTAMPTZ NOT NULL,
  machine_id TEXT NOT NULL,
  rpm DOUBLE PRECISION CHECK (rpm >= 0),
  feed_mm_min DOUBLE PRECISION CHECK (feed_mm_min >= 0),
  state TEXT CHECK (state IN ('running','stopped','idle')),
  sequence BIGINT,
  src TEXT DEFAULT 'mtconnect',
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('telemetry', 'ts', if_not_exists=>TRUE);

-- Índices otimizados
CREATE INDEX idx_machine_ts ON telemetry(machine_id, ts DESC);
CREATE INDEX idx_state ON telemetry(state, ts DESC) WHERE state \!= 'idle';

-- Retention policy (30 dias)
SELECT add_retention_policy('telemetry', INTERVAL '30 days');

-- Continuous aggregates (5min)
CREATE MATERIALIZED VIEW telemetry_5m
WITH (timescaledb.continuous) AS
  SELECT 
    time_bucket('5 minutes', ts) AS bucket,
    machine_id,
    AVG(rpm) AS rpm_avg,
    MAX(rpm) AS rpm_max,
    MIN(rpm) AS rpm_min,
    AVG(feed_mm_min) AS feed_avg,
    MAX(feed_mm_min) AS feed_max,
    COUNT(*) AS sample_count,
    MODE() WITHIN GROUP (ORDER BY state) AS state_mode
  FROM telemetry
  GROUP BY bucket, machine_id
  WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_5m',
  start_offset => INTERVAL '1 hour',
  end_offset => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '5 minutes');

-- Aggregate 1h (para dashboard diário)
CREATE MATERIALIZED VIEW telemetry_1h
WITH (timescaledb.continuous) AS
  SELECT 
    time_bucket('1 hour', bucket) AS bucket,
    machine_id,
    AVG(rpm_avg) AS rpm_avg,
    MAX(rpm_max) AS rpm_max,
    AVG(feed_avg) AS feed_avg,
    SUM(sample_count) AS sample_count
  FROM telemetry_5m
  GROUP BY 1, 2
  WITH NO DATA;
```

**Critérios de Aceite (G5):**
- ✅ Ingestão ≥ 5000 pontos/min (83 pontos/s)
- ✅ SELECT P95 < 200ms em `telemetry_5m`
- ✅ Compressão ativa após 7 dias (reduz 70% storage)
- ✅ Query histórico 30 dias < 2s

**Validação:**
```bash
# Load test (ingestão)
for i in {1..5000}; do
  curl -X POST http://localhost:8001/v1/telemetry/ingest \
    -H 'Content-Type: application/json' \
    -d "{\"machine_id\":\"TEST-001\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"rpm\":4500,\"feed_mm_min\":1400,\"state\":\"running\"}"
done &

# Query performance
psql -c "EXPLAIN ANALYZE SELECT * FROM telemetry_5m WHERE machine_id='CNC-SIM-001' AND bucket > NOW() - INTERVAL '7 days';"
```

**Referência:** https://docs.timescale.com/

---

#### **Gate 6: Alertas Proativos (Slack/Webhook)**
**Prazo:** Semana 2-3 (7-10 dias)

**Entregas:**
- Engine de regras (YAML config)
- Celery worker para avaliação assíncrona
- Integração Slack (incoming webhooks)
- Webhook genérico (HTTP POST)
- Dashboard de alertas ativos
- Dedupe (1 alerta/min por regra)

**Schema de Regras:**
```yaml
# alerts.yaml
alerts:
  - name: machine_stopped_long
    machine_id: "*"  # todas
    condition: |
      state == 'stopped' AND 
      duration_seconds > 600  # 10 min
    severity: warning
    channels:
      - type: slack
        webhook: ${SLACK_WEBHOOK_URL}
        template: "🔴 {machine_id} parada há {duration_min} min"
      - type: webhook
        url: ${ALERT_WEBHOOK_URL}
        
  - name: rpm_anomaly
    machine_id: "ABR-850"
    condition: |
      rpm > 0 AND rpm < 1000 AND state == 'running'  # RPM baixo anormal
    severity: critical
    channels:
      - type: slack

  - name: feed_zero_running
    condition: |
      feed_mm_min == 0 AND state == 'running'  # Feed parado em execução
    severity: warning
    duration_seconds: 15  # só alerta se persistir 15s
```

**Implementação (Engine):**
```python
# backend/app/services/alerts.py
from celery import Celery
import yaml
import httpx
from datetime import datetime, timedelta

celery_app = Celery('alerts', broker='redis://localhost:6379/0')

@celery_app.task
def evaluate_alerts():
    rules = load_rules('alerts.yaml')
    recent_data = query_recent_telemetry(seconds=60)
    
    for rule in rules:
        matches = eval_condition(rule['condition'], recent_data)
        if matches:
            if not is_recently_fired(rule['name'], minutes=1):
                send_alert(rule, matches)

def send_alert(rule, data):
    for channel in rule['channels']:
        if channel['type'] == 'slack':
            send_slack(channel['webhook'], format_message(rule, data))
        elif channel['type'] == 'webhook':
            send_webhook(channel['url'], data)
```

**Critérios de Aceite (G6):**
- ✅ Alerta < 5s após condição satisfeita
- ✅ Dedupe: máx 1 alerta/min por regra
- ✅ Slack recebe mensagem formatada
- ✅ Zero falsos positivos em 24h de teste

**Validação:**
```bash
# Simular condição de alerta
curl -X POST http://localhost:8001/v1/telemetry/ingest \
  -d '{"machine_id":"TEST-001","timestamp":"2025-11-05T10:00:00Z","rpm":0,"feed_mm_min":0,"state":"stopped"}'

# Aguardar 11 minutos (para trigger machine_stopped_long)
sleep 660

# Verificar Slack recebeu notificação
curl -X GET http://localhost:8001/v1/alerts/history | jq
```

---

#### **Gate 7: Multi-Máquina (10 CNCs Simultâneos)**
**Prazo:** Semana 3-4 (7-10 dias)

**Entregas:**
- Adapter multi-threaded (ThreadPoolExecutor)
- Config YAML para lista de máquinas
- Dashboard: Grid de máquinas
- Filtros: estado, planta, modelo
- Endpoint `/v1/fleet/summary`
- Agregação: OEE médio, uptime total

**Config Multi-Máquina:**
```yaml
# machines.yaml
machines:
  - id: ABR-850
    agent_url: http://10.0.1.50:5000
    plant: "Planta 1"
    model: "ABR-850"
    
  - id: CNC-SIM-001
    agent_url: http://localhost:5000
    plant: "Lab"
    model: "Simulator"
    
  - id: CNC-SIM-002
    agent_url: http://localhost:5001
    plant: "Lab"
    model: "Simulator"
    
  # ... até 10 máquinas
```

**Adapter Multi-Thread:**
```python
# backend/mtconnect_adapter.py
from concurrent.futures import ThreadPoolExecutor
import yaml

def run_multi_machine(config_file='machines.yaml'):
    machines = yaml.safe_load(open(config_file))['machines']
    
    with ThreadPoolExecutor(max_workers=len(machines)) as executor:
        futures = []
        for machine in machines:
            adapter = MTConnectAdapter(
                agent_url=machine['agent_url'],
                api_url=API_URL,
                machine_id=machine['id']
            )
            futures.append(executor.submit(asyncio.run, adapter.run()))
        
        # Wait all
        for future in futures:
            future.result()
```

**Fleet Summary API:**
```python
@router.get("/v1/fleet/summary")
def get_fleet_summary():
    machines = db.query("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN state='running' THEN 1 ELSE 0 END) AS running,
            SUM(CASE WHEN state='stopped' THEN 1 ELSE 0 END) AS stopped,
            SUM(CASE WHEN state='idle' THEN 1 ELSE 0 END) AS idle,
            AVG(rpm) AS avg_rpm,
            AVG(oee_availability * oee_performance) AS avg_oee
        FROM latest_status
    """)
    return machines
```

**Critérios de Aceite (G7):**
- ✅ 10 máquinas simultâneas sem degradação
- ✅ Perda de dados < 0.5% em 1h
- ✅ P95 latência ingestão < 2s
- ✅ Falha em 1 máquina não afeta outras
- ✅ Dashboard renderiza < 1s com 10 máquinas

**Validação:**
```bash
# Subir 10 simuladores em portas diferentes
for i in {5000..5009}; do
  python3 scripts/mtconnect_simulator.py --port $i &
done

# Configurar machines.yaml com 10 entradas

# Rodar adapter multi-máquina
python3 backend/mtconnect_adapter.py --config machines.yaml

# Load test
ab -n 1000 -c 10 http://localhost:8001/v1/fleet/summary

# Validar métricas
psql -c "SELECT machine_id, COUNT(*) FROM telemetry WHERE ts > NOW() - INTERVAL '1 hour' GROUP BY machine_id;"
```

---

### 📊 Próximos 3-9 Meses — ANALYTICS & OBSERVABILIDADE (F8-F12)

#### **Gate 8: OEE & Analytics Dashboard**
**Prazo:** Q1 2026 (4-6 semanas)

**OEE Canonical:**
```
OEE = Availability × Performance × Quality

Availability = Operating Time / Planned Production Time
Performance = (Actual Output / Theoretical Max Output)
Quality = (Good Parts / Total Parts Produced)
```

**Entregas:**
- Cálculo OEE por máquina/turno/dia
- Dashboard: Cards OEE, Trends, Heatmaps
- Endpoint `/v1/machines/{id}/oee?date=YYYY-MM-DD`
- Agregações: OEE médio por planta
- Export PDF/CSV

**Schema OEE:**
```sql
CREATE TABLE oee_daily (
  date DATE NOT NULL,
  machine_id TEXT NOT NULL,
  planned_time_min INT NOT NULL,
  operating_time_min INT NOT NULL,
  actual_parts INT,
  theoretical_parts INT,
  good_parts INT,
  availability FLOAT,
  performance FLOAT,
  quality FLOAT,
  oee FLOAT,
  PRIMARY KEY (date, machine_id)
);
```

**Critérios de Aceite (G8):**
- ✅ OEE calculado por máquina/turno/dia
- ✅ Dashboard mostra trends 30 dias
- ✅ Query OEE < 500ms
- ✅ Export PDF em < 3s

---

#### **Gate 9: OPC-UA Bridge (IEC 62541)**
**Prazo:** Q1 2026 (3-4 semanas)

**Entregas:**
- Cliente OPC-UA (asyncua)
- Auto-discovery de nodes
- Mapeamento Speed/Feed/Execution → schema
- Coexistência com MTConnect

**PoC:**
```python
from asyncua import Client

async def opc_ua_adapter():
    client = Client("opc.tcp://10.0.1.100:4840")
    await client.connect()
    
    # Browse nodes
    root = client.get_root_node()
    cnc_node = await root.get_child(["Objects", "CNC", "Machine1"])
    
    # Subscribe
    speed_node = await cnc_node.get_child(["Speed"])
    feed_node = await cnc_node.get_child(["Feed"])
    
    while True:
        speed = await speed_node.read_value()
        feed = await feed_node.read_value()
        
        await post_ingest({
            "machine_id": "OPC-001",
            "rpm": speed,
            "feed_mm_min": feed * 60,  # mm/s → mm/min
            "state": "running"
        })
        await asyncio.sleep(2)
```

**Critérios de Aceite (G9):**
- ✅ 30 min amostras sem perda
- ✅ Doc de mapeamento nodes → schema
- ✅ Coexiste com MTConnect

---

#### **Gate 10: Observabilidade (OpenTelemetry)**
**Prazo:** Q2 2026 (2-3 semanas)

**Entregas:**
- Instrumentação FastAPI (OTEL)
- Métricas: ingest_rate, queue_lag, api_latency
- Traces: /ingest E2E
- Export para Jaeger/Prometheus

**Instrumentação:**
```python
# backend/app.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
)

# Trace /ingest
@app.post("/v1/telemetry/ingest")
@tracer.start_as_current_span("ingest_telemetry")
async def ingest(payload: TelemetryPayload):
    span = trace.get_current_span()
    span.set_attribute("machine_id", payload.machine_id)
    # ... lógica
```

**Critérios de Aceite (G10):**
- ✅ Métricas exportadas (ingest_rate, lag)
- ✅ Traces de /ingest no Jaeger
- ✅ Dashboards Grafana com SLIs

**Referência:** https://opentelemetry.io/

---

#### **Gate 11: Edge PoC (MQTT + Buffer Offline)**
**Prazo:** Q2 2026 (4 semanas)

**Entregas:**
- MQTT pub/sub (Mosquitto)
- Buffer local (SQLite) durante offline
- Re-envio automático após reconexão
- QoS 1 (at least once)

**Arquitetura:**
```
CNC → Adapter Edge → MQTT Broker → Cloud Subscriber → Backend
              ↓
         SQLite Buffer
         (durante offline)
```

**Implementação:**
```python
import paho.mqtt.client as mqtt
import sqlite3

class EdgeAdapter:
    def __init__(self):
        self.buffer = sqlite3.connect('edge_buffer.db')
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.connect("mqtt.example.com", 1883)
    
    def publish_telemetry(self, data):
        try:
            self.mqtt_client.publish(
                f"telemetry/{data['machine_id']}", 
                json.dumps(data), 
                qos=1
            )
        except:
            # Offline: buffer localmente
            self.buffer_insert(data)
    
    def on_connect(self, client, userdata, flags, rc):
        # Reconectou: enviar buffer
        buffered = self.buffer_read()
        for item in buffered:
            self.publish_telemetry(item)
        self.buffer_clear()
```

**Critérios de Aceite (G11):**
- ✅ 15 min offline sem perda de dados
- ✅ Re-envio automático após reconexão
- ✅ QoS 1 garantido

---

#### **Gate 12: Trilhas de Conformidade (SOC 2 / ISO 27001)**
**Prazo:** Q3-Q4 2026 (16 semanas + auditoria)

**SOC 2 Trust Services Criteria (TSC):**
- **CC6.1:** Change Management (CI/CD, Git commits, aprovações)
- **CC6.2:** Access Control (RBAC, MFA, audit log)
- **CC7.2:** Logging & Monitoring (90 dias retenção)

**ISO 27001 Anexo A:**
- **A.9.2:** User access management
- **A.12.3:** Information backup
- **A.18.1:** Compliance com requisitos legais

**Ações Imediatas:**
- [ ] Política de segurança aprovada (escopo ISMS)
- [ ] CI/CD com aprovação (GitHub branch protection)
- [ ] RBAC implementado (admin, operator, viewer)
- [ ] Audit log 90 dias (PostgreSQL table)
- [ ] Encryption at rest (AES-256)
- [ ] Encryption in transit (TLS 1.3)

**Critérios de Aceite (G12):**
- ✅ Política de segurança aprovada
- ✅ Evidências mínimas: CI/CD, RBAC, logs
- ✅ Backup automático diário
- ✅ Penetration test sem critical findings

---

### 🌐 9-24 Meses — ENTERPRISE SCALE (F13-F20)

#### **F13:** Multi-Tenant SaaS (schema-per-tenant)
#### **F14:** Integrações ERP/MES (SAP, Wonderware)
#### **F15:** Mobile App (React Native)
#### **F16:** Certificações (SOC 2 Type II, ISO 27001)
#### **F17:** Escalonamento Multi-Região (AWS/GCP)
#### **F18:** Plugin Marketplace
#### **F19:** AI Copilot (LangChain + GPT-4)
#### **F20:** Global Scale (K8s multi-cluster)

---

## 📊 SLOs e Métricas

### SLIs (Service Level Indicators)
- **Availability:** Uptime API (target: 99.5% Q4, 99.9% Q2'26)
- **Latency:** P95 /ingest < 2s, P99 < 5s
- **Durability:** Perda de dados < 0.5%
- **Throughput:** Ingestão ≥ 5000 pontos/min

### OEE Targets (Cliente)
- **Q4'25:** Baseline (medir sem alvo)
- **Q1'26:** OEE médio > 60%
- **Q2'26:** OEE médio > 75%

### Business Metrics
- **Máquinas monitoradas:** 1 → 10 (30d) → 50 (Q1) → 100 (Q2)
- **Clientes:** 1 → 3 (Q1) → 10 (Q2)
- **ARR:** $0 → $10k (Q1) → $50k (Q2)

---

## 🚧 Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| **Heterogeneidade MTConnect** | Alto | Tabela de mapeamento por fornecedor/versão |
| **Cardinalidade explode DB** | Crítico | Retenção 30d + continuous aggregates |
| **Vendor lock-in edge** | Médio | Alternativas: Greengrass, Azure IoT Edge |
| **Compliance atraso** | Alto | Milestones trimestrais SOC 2/ISO 27001 |
| **OPC-UA complexidade** | Médio | PoC limitado a 3 fornecedores primeiro |

---

## 🎯 Próximo Passo Cirúrgico

### Hoje (5 Nov)
- [x] Roadmap revisado
- [ ] Iniciar F5: Criar schema TimescaleDB
- [ ] Setup PostgreSQL + TimescaleDB extension

### Esta Semana (6-10 Nov)
- [ ] F4 campo: Soak 30 min ABR-850 + registrar OEE diário
- [ ] F5: Hypertable + retention policy
- [ ] F5: Migrar /ingest para gravar em DB

### Próximos 30 Dias
- [ ] F5 completo (histórico 30d)
- [ ] F6 completo (alertas Slack)
- [ ] F7 completo (10 CNCs)
- [ ] Primeira venda (cliente beta pagante)

---

## 📚 Bases Normativas

### MTConnect
- **Sequências:** `Header.nextSequence` + `from` em `/sample`
- **Incremental:** Consumo sem perdas
- **Spec:** https://www.mtconnect.org/

### OPC-UA (IEC 62541)
- **Interoperabilidade:** Padrão industrial universal
- **Coexistência:** MTConnect + OPC-UA simultaneamente
- **Spec:** https://opcfoundation.org/

### OEE
- **Fórmula:** A × P × Q
- **ROI:** Métrica âncora para cliente
- **Ref:** ISA-95, SEMI E10

### MQTT
- **Pub/Sub:** Tópicos + QoS para links ruins
- **Edge:** Ideal para telemetria edge↔cloud
- **Spec:** OASIS MQTT 5.0

### OpenTelemetry
- **Observabilidade:** Métricas + Traces + Logs
- **SLOs:** Facilita troubleshooting
- **Ref:** https://opentelemetry.io/

### TimescaleDB
- **Time-Series:** Agregações + compressão nativa
- **PostgreSQL:** Compatível com ecossistema
- **Docs:** https://docs.timescale.com/

---

**Versão:** 2.0  
**Autor:** Vinicius John  
**Última Atualização:** 2025-11-05  
**Próxima Revisão:** 2025-12-05
