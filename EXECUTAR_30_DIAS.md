# ⚡ Plano de Execução 30 Dias — F5, F6, F7

**Objetivo:** Travar valor comercial com histórico, alertas e multi-máquina  
**Prazo:** 5 Nov → 5 Dez 2025  
**Gates:** G5 (Histórico), G6 (Alertas), G7 (Multi-máquina)

---

## 📅 Semana 1 (5-12 Nov) — F5 Histórico TimescaleDB

### Dia 1-2: Setup PostgreSQL + TimescaleDB

```bash
# Instalar PostgreSQL 15 + TimescaleDB
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-15

# Configurar TimescaleDB
sudo timescaledb-tune --quiet --yes

# Restart PostgreSQL
sudo systemctl restart postgresql

# Criar database
sudo -u postgres psql -c "CREATE DATABASE cnc_telemetry;"
sudo -u postgres psql -d cnc_telemetry -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# Criar user
sudo -u postgres psql -c "CREATE USER cnc_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cnc_telemetry TO cnc_user;"
```

### Dia 3: Schema + Hypertables

```sql
-- Conectar
psql -U cnc_user -d cnc_telemetry

-- Schema principal
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

-- Criar hypertable (particionamento automático)
SELECT create_hypertable('telemetry', 'ts', if_not_exists=>TRUE);

-- Índices otimizados
CREATE INDEX idx_machine_ts ON telemetry(machine_id, ts DESC);
CREATE INDEX idx_state_ts ON telemetry(state, ts DESC) WHERE state != 'idle';
CREATE INDEX idx_sequence ON telemetry(sequence) WHERE sequence IS NOT NULL;

-- Retention policy (30 dias)
SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists=>TRUE);

-- Compression (após 7 dias, reduz 70% storage)
ALTER TABLE telemetry SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'machine_id',
  timescaledb.compress_orderby = 'ts DESC'
);

SELECT add_compression_policy('telemetry', INTERVAL '7 days', if_not_exists=>TRUE);
```

### Dia 4: Continuous Aggregates

```sql
-- Aggregate 5 minutos (para queries rápidas)
CREATE MATERIALIZED VIEW telemetry_5m
WITH (timescaledb.continuous) AS
  SELECT 
    time_bucket('5 minutes', ts) AS bucket,
    machine_id,
    AVG(rpm) AS rpm_avg,
    MAX(rpm) AS rpm_max,
    MIN(rpm) AS rpm_min,
    STDDEV(rpm) AS rpm_stddev,
    AVG(feed_mm_min) AS feed_avg,
    MAX(feed_mm_min) AS feed_max,
    COUNT(*) AS sample_count,
    MODE() WITHIN GROUP (ORDER BY state) AS state_mode,
    SUM(CASE WHEN state='running' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS uptime_ratio
  FROM telemetry
  GROUP BY bucket, machine_id
  WITH NO DATA;

-- Refresh policy (atualiza a cada 5 min)
SELECT add_continuous_aggregate_policy('telemetry_5m',
  start_offset => INTERVAL '1 hour',
  end_offset => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '5 minutes',
  if_not_exists => TRUE
);

-- Aggregate 1 hora (para dashboard diário/semanal)
CREATE MATERIALIZED VIEW telemetry_1h
WITH (timescaledb.continuous) AS
  SELECT 
    time_bucket('1 hour', bucket) AS bucket,
    machine_id,
    AVG(rpm_avg) AS rpm_avg,
    MAX(rpm_max) AS rpm_max,
    AVG(feed_avg) AS feed_avg,
    SUM(sample_count) AS sample_count,
    AVG(uptime_ratio) AS uptime_ratio
  FROM telemetry_5m
  GROUP BY 1, 2
  WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_1h',
  start_offset => INTERVAL '3 hours',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE
);

-- Aggregate 1 dia (para relatórios mensais)
CREATE MATERIALIZED VIEW telemetry_1d
WITH (timescaledb.continuous) AS
  SELECT 
    time_bucket('1 day', bucket) AS date,
    machine_id,
    AVG(rpm_avg) AS rpm_avg,
    MAX(rpm_max) AS rpm_max,
    AVG(feed_avg) AS feed_avg,
    SUM(sample_count) AS sample_count,
    AVG(uptime_ratio) AS availability
  FROM telemetry_1h
  GROUP BY 1, 2
  WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_1d',
  start_offset => INTERVAL '1 day',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);
```

### Dia 5-7: Backend Integration

```bash
# Instalar drivers
cd backend
source .venv/bin/activate
pip install psycopg2-binary asyncpg sqlalchemy alembic

# Adicionar ao requirements.txt
echo "psycopg2-binary==2.9.9" >> requirements.txt
echo "asyncpg==0.29.0" >> requirements.txt
echo "sqlalchemy==2.0.23" >> requirements.txt
echo "alembic==1.13.0" >> requirements.txt
```

```python
# backend/app/db.py
from sqlalchemy import create_engine, Column, Float, String, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

DATABASE_URL = "postgresql://cnc_user:your_password@localhost/cnc_telemetry"

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    ts = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    machine_id = Column(String(50), primary_key=True, nullable=False)
    rpm = Column(Float, nullable=False)
    feed_mm_min = Column(Float, nullable=False)
    state = Column(String(20), nullable=False)
    sequence = Column(BigInteger, nullable=True)
    src = Column(String(20), default="mtconnect")
    ingested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# backend/app.py (modificar /ingest)
from app.db import get_db, Telemetry

@app.post("/v1/telemetry/ingest", status_code=201)
async def ingest_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    # Salvar no DB
    db_record = Telemetry(
        ts=datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00')),
        machine_id=payload.machine_id,
        rpm=payload.rpm,
        feed_mm_min=payload.feed_mm_min,
        state=payload.state
    )
    db.add(db_record)
    db.commit()
    
    # Atualizar status no store (para /status)
    status.update_status(
        machine_id=payload.machine_id,
        rpm=payload.rpm,
        feed_mm_min=payload.feed_mm_min,
        state=payload.state
    )
    
    return {
        "ingested": True,
        "machine_id": payload.machine_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

### Endpoint `/history`

```python
# backend/app/routers/history.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from datetime import datetime

router = APIRouter(prefix="/v1/machines", tags=["history"])

@router.get("/{machine_id}/history")
def get_history(
    machine_id: str,
    from_ts: str = Query(..., description="ISO 8601"),
    to_ts: str = Query(..., description="ISO 8601"),
    resolution: str = Query("5m", description="raw | 5m | 1h | 1d"),
    db: Session = Depends(get_db)
):
    from_dt = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
    to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
    
    if resolution == "raw":
        table = "telemetry"
        ts_col = "ts"
    elif resolution == "5m":
        table = "telemetry_5m"
        ts_col = "bucket"
    elif resolution == "1h":
        table = "telemetry_1h"
        ts_col = "bucket"
    elif resolution == "1d":
        table = "telemetry_1d"
        ts_col = "date"
    
    query = f"""
        SELECT * FROM {table}
        WHERE machine_id = :machine_id
          AND {ts_col} >= :from_ts
          AND {ts_col} <= :to_ts
        ORDER BY {ts_col} DESC
        LIMIT 10000
    """
    
    result = db.execute(query, {
        "machine_id": machine_id,
        "from_ts": from_dt,
        "to_ts": to_dt
    })
    
    return [dict(row) for row in result]
```

### Validação G5

```bash
# Load test ingestão
for i in {1..5000}; do
  curl -s -X POST http://localhost:8001/v1/telemetry/ingest \
    -H 'Content-Type: application/json' \
    -d "{\"machine_id\":\"TEST-001\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"rpm\":4500,\"feed_mm_min\":1400,\"state\":\"running\"}" &
done
wait

# Verificar ingestão
psql -U cnc_user -d cnc_telemetry -c "SELECT COUNT(*) FROM telemetry WHERE machine_id='TEST-001';"

# Query performance (P95 < 200ms)
psql -U cnc_user -d cnc_telemetry -c "EXPLAIN ANALYZE SELECT * FROM telemetry_5m WHERE machine_id='CNC-SIM-001' AND bucket > NOW() - INTERVAL '7 days';"

# Histórico 30 dias (< 2s)
time curl "http://localhost:8001/v1/machines/CNC-SIM-001/history?from_ts=2025-10-05T00:00:00Z&to_ts=2025-11-05T00:00:00Z&resolution=1h"
```

**✅ Critérios de Aceite G5:**
- Ingestão ≥ 5000 pontos/min
- SELECT P95 < 200ms
- Query 30 dias < 2s
- Compression ativa após 7 dias

---

## 📅 Semana 2-3 (13-26 Nov) — F6 Alertas

### Setup Celery + Redis

```bash
# Instalar Redis
sudo apt install -y redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Backend dependencies
cd backend
pip install celery redis pyyaml httpx
echo "celery==5.3.4" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt
echo "pyyaml==6.0.1" >> requirements.txt
```

### Engine de Alertas

```python
# backend/app/services/alerts.py
from celery import Celery
import yaml
import httpx
from datetime import datetime, timedelta
from sqlalchemy import text
from app.db import engine

celery_app = Celery('alerts', broker='redis://localhost:6379/0')

# Cache de alertas recentes (dedupe)
recent_alerts = {}

@celery_app.task
def evaluate_alerts():
    """Executar a cada 30s via Celery Beat"""
    rules = load_rules('/home/viniciusjohn/iot/config/alerts.yaml')
    
    for rule in rules:
        # Query dados recentes
        recent_data = query_recent(rule, seconds=60)
        
        # Avaliar condição
        if eval_condition(rule['condition'], recent_data):
            # Verificar dedupe (1/min)
            alert_key = f"{rule['name']}:{rule.get('machine_id', '*')}"
            last_fired = recent_alerts.get(alert_key)
            
            if not last_fired or (datetime.now() - last_fired).seconds > 60:
                send_alert(rule, recent_data)
                recent_alerts[alert_key] = datetime.now()

def eval_condition(condition, data):
    """Avaliar expressão Python segura"""
    # Parse condition: "state == 'stopped' AND duration_seconds > 600"
    # Simplificado: implementar parser seguro ou usar biblioteca como simpleeval
    
    if not data:
        return False
    
    latest = data[0]
    
    # Exemplo simples
    if "state == 'stopped'" in condition and latest['state'] == 'stopped':
        if 'duration_seconds' in condition:
            duration = (datetime.now() - latest['ts']).seconds
            return duration > 600  # 10 min
    
    return False

def send_alert(rule, data):
    for channel in rule['channels']:
        if channel['type'] == 'slack':
            send_slack(channel['webhook'], format_slack_message(rule, data))
        elif channel['type'] == 'webhook':
            send_webhook(channel['url'], format_webhook_payload(rule, data))

def send_slack(webhook_url, message):
    httpx.post(webhook_url, json={"text": message})

def format_slack_message(rule, data):
    machine = data[0]['machine_id']
    state = data[0]['state']
    duration = (datetime.now() - data[0]['ts']).seconds // 60
    
    emoji = "🔴" if rule['severity'] == 'critical' else "⚠️"
    return f"{emoji} {machine}: {rule['name']} - Estado {state} há {duration} min"
```

### Celery Beat (Scheduler)

```python
# backend/celerybeat_config.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery('alerts', broker='redis://localhost:6379/0')

celery_app.conf.beat_schedule = {
    'evaluate-alerts': {
        'task': 'app.services.alerts.evaluate_alerts',
        'schedule': 30.0,  # a cada 30s
    },
}
```

### Config de Alertas

```yaml
# config/alerts.yaml
alerts:
  - name: machine_stopped_long
    machine_id: "*"  # todas
    condition: "state == 'stopped' AND duration_seconds > 600"
    severity: warning
    channels:
      - type: slack
        webhook: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
        
  - name: rpm_low_anomaly
    machine_id: "ABR-850"
    condition: "rpm > 0 AND rpm < 1000 AND state == 'running'"
    severity: critical
    channels:
      - type: slack
        webhook: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Rodar Celery

```bash
# Terminal 1: Worker
cd backend
source .venv/bin/activate
celery -A app.services.alerts worker --loglevel=info

# Terminal 2: Beat (scheduler)
celery -A app.services.alerts beat --loglevel=info
```

### Validação G6

```bash
# Simular máquina parada
curl -X POST http://localhost:8001/v1/telemetry/ingest \
  -d '{"machine_id":"TEST-001","timestamp":"2025-11-05T10:00:00Z","rpm":0,"feed_mm_min":0,"state":"stopped"}'

# Aguardar 11 minutos
sleep 660

# Verificar Slack recebeu alerta
# Verificar logs Celery
tail -f celery.log
```

**✅ Critérios de Aceite G6:**
- Alerta < 5s após condição
- Dedupe: máx 1 alerta/min
- Slack recebe mensagem formatada
- Zero falsos positivos em 24h

---

## 📅 Semana 4 (27 Nov - 5 Dez) — F7 Multi-Máquina

### Config Multi-Máquina

```yaml
# config/machines.yaml
machines:
  - id: ABR-850
    agent_url: http://10.0.1.50:5000
    plant: "Planta 1"
    model: "ABR-850"
    location: "SP"
    
  - id: CNC-SIM-001
    agent_url: http://localhost:5000
    plant: "Lab"
    model: "Simulator"
    location: "Lab"
    
  - id: CNC-SIM-002
    agent_url: http://localhost:5001
    plant: "Lab"
    model: "Simulator"
    location: "Lab"
```

### Adapter Multi-Thread

```python
# backend/mtconnect_adapter.py (modificar)
from concurrent.futures import ThreadPoolExecutor
import yaml

def run_multi_machine(config_file='config/machines.yaml'):
    """Rodar adapter para múltiplas máquinas em paralelo"""
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    machines = config['machines']
    
    with ThreadPoolExecutor(max_workers=len(machines)) as executor:
        futures = []
        
        for machine in machines:
            logger.info(f"Iniciando adapter para {machine['id']}")
            
            adapter = MTConnectAdapter(
                agent_url=machine['agent_url'],
                api_url="http://localhost:8001",
                machine_id=machine['id']
            )
            
            future = executor.submit(asyncio.run, adapter.run())
            futures.append(future)
        
        # Aguardar todos
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Erro no adapter: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/machines.yaml')
    args = parser.parse_args()
    
    run_multi_machine(args.config)
```

### Fleet Summary API

```python
# backend/app/routers/fleet.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db

router = APIRouter(prefix="/v1/fleet", tags=["fleet"])

@router.get("/summary")
def get_fleet_summary(db: Session = Depends(get_db)):
    """Resumo de todas as máquinas"""
    query = """
        SELECT 
            COUNT(DISTINCT machine_id) AS total_machines,
            SUM(CASE WHEN state='running' THEN 1 ELSE 0 END) AS running,
            SUM(CASE WHEN state='stopped' THEN 1 ELSE 0 END) AS stopped,
            SUM(CASE WHEN state='idle' THEN 1 ELSE 0 END) AS idle,
            AVG(rpm) AS avg_rpm,
            AVG(feed_mm_min) AS avg_feed
        FROM (
            SELECT DISTINCT ON (machine_id) *
            FROM telemetry
            ORDER BY machine_id, ts DESC
        ) latest
    """
    
    result = db.execute(query).fetchone()
    
    return {
        "total_machines": result.total_machines,
        "running": result.running,
        "stopped": result.stopped,
        "idle": result.idle,
        "avg_rpm": round(result.avg_rpm, 1) if result.avg_rpm else 0,
        "avg_feed": round(result.avg_feed, 1) if result.avg_feed else 0
    }

@router.get("/machines")
def list_machines(db: Session = Depends(get_db)):
    """Lista de máquinas com status"""
    query = """
        SELECT DISTINCT ON (machine_id)
            machine_id,
            ts,
            rpm,
            feed_mm_min,
            state
        FROM telemetry
        ORDER BY machine_id, ts DESC
    """
    
    result = db.execute(query).fetchall()
    
    return [
        {
            "machine_id": row.machine_id,
            "last_seen": row.ts.isoformat(),
            "rpm": row.rpm,
            "feed_mm_min": row.feed_mm_min,
            "state": row.state
        }
        for row in result
    ]
```

### Dashboard Multi-Máquina

```typescript
// frontend/src/components/FleetDashboard.tsx
import { useEffect, useState } from 'react';

interface FleetSummary {
  total_machines: number;
  running: number;
  stopped: number;
  idle: number;
  avg_rpm: number;
  avg_feed: number;
}

interface Machine {
  machine_id: string;
  state: string;
  rpm: number;
  feed_mm_min: number;
  last_seen: string;
}

export function FleetDashboard() {
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  
  useEffect(() => {
    async function fetchFleet() {
      const summaryRes = await fetch('http://localhost:8001/v1/fleet/summary');
      const summaryData = await summaryRes.json();
      setSummary(summaryData);
      
      const machinesRes = await fetch('http://localhost:8001/v1/fleet/machines');
      const machinesData = await machinesRes.json();
      setMachines(machinesData);
    }
    
    fetchFleet();
    const interval = setInterval(fetchFleet, 5000);  // a cada 5s
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div>
      <h1>Fleet Overview</h1>
      
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <Card title="Total Machines" value={summary.total_machines} />
          <Card title="Running" value={summary.running} color="green" />
          <Card title="Stopped" value={summary.stopped} color="red" />
          <Card title="Idle" value={summary.idle} color="yellow" />
        </div>
      )}
      
      <h2>Machines</h2>
      <div className="grid grid-cols-3 gap-4">
        {machines.map(m => (
          <MachineCard key={m.machine_id} machine={m} />
        ))}
      </div>
    </div>
  );
}
```

### Validação G7

```bash
# Subir 10 simuladores
for i in {5000..5009}; do
  python3 scripts/mtconnect_simulator.py --port $i &
done

# Criar config/machines.yaml com 10 entradas

# Rodar adapter multi-máquina
python3 backend/mtconnect_adapter.py --config config/machines.yaml

# Load test
ab -n 1000 -c 10 http://localhost:8001/v1/fleet/summary

# Verificar perda de dados
psql -U cnc_user -d cnc_telemetry -c "
  SELECT machine_id, COUNT(*) 
  FROM telemetry 
  WHERE ts > NOW() - INTERVAL '1 hour' 
  GROUP BY machine_id 
  ORDER BY COUNT(*) DESC;
"

# Validar < 0.5% perda
# Esperado: ~1800 amostras/máquina em 1h (1 amostra/2s)
# Aceite: >= 1791 amostras (99.5%)
```

**✅ Critérios de Aceite G7:**
- 10 máquinas simultâneas sem degradação
- Perda < 0.5% em 1h
- P95 latência < 2s
- Falha em 1 máquina não afeta outras
- Dashboard < 1s render

---

## 📊 Métricas de Sucesso 30 Dias

| Métrica | Baseline | Target 30d | Validação |
|---------|----------|------------|-----------|
| **Máquinas Monitoradas** | 1 | 10 | `SELECT COUNT(DISTINCT machine_id) FROM telemetry` |
| **Perda de Dados** | — | < 0.5% | Compare expected vs actual samples |
| **Latência P95 /ingest** | — | < 2s | OpenTelemetry metrics |
| **Query Histórico 30d** | — | < 2s | `time curl .../history` |
| **Alertas Ativos** | 0 | ≥ 3 regras | `config/alerts.yaml` |
| **Uptime API** | — | > 99% | Prometheus monitoring |

---

## 🎯 Checklist Final 30 Dias

- [ ] **G5 PASS:** Histórico 30 dias (TimescaleDB)
  - [ ] Hypertable criada
  - [ ] Retention policy ativa
  - [ ] Continuous aggregates (5m, 1h, 1d)
  - [ ] Endpoint `/history` funcionando
  - [ ] Load test: ≥ 5k pontos/min
  - [ ] Query < 2s

- [ ] **G6 PASS:** Alertas proativos
  - [ ] Celery + Redis configurados
  - [ ] 3+ regras de alerta
  - [ ] Integração Slack funcionando
  - [ ] Dedupe (1 alerta/min)
  - [ ] Latência < 5s

- [ ] **G7 PASS:** Multi-máquina (10 CNCs)
  - [ ] Adapter multi-thread
  - [ ] Config YAML 10 máquinas
  - [ ] Fleet summary API
  - [ ] Dashboard grid
  - [ ] Perda < 0.5%
  - [ ] Render < 1s

- [ ] **Cliente Beta:** 1 cliente pagante fechado
- [ ] **Documentação:** README atualizado com setup
- [ ] **Deploy:** Staging environment funcionando

---

**🚀 Ao final de 30 dias, você terá:**
- Sistema com histórico de 30 dias
- Alertas proativos em Slack
- 10 máquinas monitoradas simultaneamente
- Base sólida para OEE e analytics
- Produto demonstrável para clientes beta

**💰 Valor comercial travado!**
