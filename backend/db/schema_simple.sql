-- CNC Telemetry — PostgreSQL Schema (sem TimescaleDB)
-- Versão simplificada para demonstração

-- Main telemetry table
CREATE TABLE IF NOT EXISTS telemetry (
  ts TIMESTAMPTZ NOT NULL,
  machine_id TEXT NOT NULL,
  rpm DOUBLE PRECISION CHECK (rpm >= 0),
  feed_mm_min DOUBLE PRECISION CHECK (feed_mm_min >= 0),
  state TEXT CHECK (state IN ('running','stopped','idle')),
  sequence BIGINT,
  src TEXT DEFAULT 'mtconnect',
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (machine_id, ts)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_machine_ts ON telemetry(machine_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_state_ts ON telemetry(state, ts DESC) WHERE state != 'idle';
CREATE INDEX IF NOT EXISTS idx_telemetry_sequence ON telemetry(sequence) WHERE sequence IS NOT NULL;

-- Grant permissions
GRANT ALL ON telemetry TO cnc_user;

-- Note: Para produção, recomenda-se TimescaleDB para:
-- - Hypertables (particionamento automático)
-- - Continuous aggregates (agregações pré-calculadas)
-- - Retention policies (remoção automática de dados antigos)
-- - Compression (economia de 70% de espaço)
