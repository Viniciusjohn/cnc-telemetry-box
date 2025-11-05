# 🎯 Gates de Validação — Critérios Objetivos

**Propósito:** Garantir qualidade através de métricas mensuráveis, não opiniões  
**Metodologia:** Command-line tests + observabilidade + SLOs

---

## Gate 5: Histórico 30 Dias (TimescaleDB)

### Critérios de Aceite
| # | Critério | Target | Comando de Validação |
|---|----------|--------|----------------------|
| 5.1 | Ingestão throughput | ≥ 5000 pontos/min | Ver script abaixo |
| 5.2 | Query P95 latency | < 200ms | EXPLAIN ANALYZE + pg_stat_statements |
| 5.3 | Histórico 30 dias query | < 2s | `time curl .../history` |
| 5.4 | Compression ratio | ≥ 70% após 7d | `SELECT compress_chunk()` |
| 5.5 | Retention automático | 30 dias | Verificar policy |

### Comandos de Validação

```bash
# 5.1 - Load test ingestão (5000 pontos em 1 min)
time for i in {1..5000}; do
  curl -s -X POST http://localhost:8001/v1/telemetry/ingest \
    -H 'Content-Type: application/json' \
    -d "{\"machine_id\":\"LOAD-TEST\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\",\"rpm\":$((RANDOM%5000)),\"feed_mm_min\":$((RANDOM%2000)),\"state\":\"running\"}" &
  
  # Rate limit (83/s = 5000/60s)
  if (( i % 83 == 0 )); then
    sleep 1
  fi
done
wait

# Verificar
psql -U cnc_user -d cnc_telemetry -c "
  SELECT 
    COUNT(*) AS total_ingested,
    COUNT(*) / EXTRACT(EPOCH FROM (MAX(ts) - MIN(ts))) * 60 AS points_per_min
  FROM telemetry 
  WHERE machine_id='LOAD-TEST' 
    AND ts > NOW() - INTERVAL '2 minutes';
"
# Esperado: points_per_min >= 5000

# 5.2 - Query P95 latency (deve ser < 200ms)
psql -U cnc_user -d cnc_telemetry -c "
  EXPLAIN (ANALYZE, BUFFERS) 
  SELECT * 
  FROM telemetry_5m 
  WHERE machine_id='CNC-SIM-001' 
    AND bucket > NOW() - INTERVAL '7 days'
  ORDER BY bucket DESC;
"
# Verificar "Execution Time: XXX ms" < 200ms

# 5.3 - Histórico 30 dias (< 2s)
time curl -s "http://localhost:8001/v1/machines/CNC-SIM-001/history?from_ts=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)&to_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)&resolution=1h" | jq length
# real < 2.0s

# 5.4 - Compression ratio
psql -U cnc_user -d cnc_telemetry -c "
  SELECT 
    pg_size_pretty(before_compression_total_bytes) AS before,
    pg_size_pretty(after_compression_total_bytes) AS after,
    ROUND((1 - after_compression_total_bytes::numeric / before_compression_total_bytes) * 100, 2) AS ratio_pct
  FROM timescaledb_information.compression_settings
  WHERE hypertable_name = 'telemetry';
"
# ratio_pct >= 70%

# 5.5 - Retention policy ativa
psql -U cnc_user -d cnc_telemetry -c "
  SELECT * FROM timescaledb_information.jobs
  WHERE proc_name = 'policy_retention';
"
# Verificar schedule_interval = '1 day', config retention = '30 days'
```

### Evidências Requeridas
- [ ] Screenshot de load test (5000 pontos/min)
- [ ] EXPLAIN ANALYZE output (P95 < 200ms)
- [ ] `time` output de query 30 dias (< 2s)
- [ ] Compression stats (≥ 70%)
- [ ] Retention policy config

---

## Gate 6: Alertas Proativos

### Critérios de Aceite
| # | Critério | Target | Comando de Validação |
|---|----------|--------|----------------------|
| 6.1 | Latência alerta | < 5s | Timestamp diff |
| 6.2 | Dedupe rate | 1 alerta/min | Log analysis |
| 6.3 | Slack delivery | 100% | Webhook logs |
| 6.4 | Falsos positivos | 0 em 24h | Manual review |
| 6.5 | Cobertura regras | ≥ 3 regras | `alerts.yaml` |

### Comandos de Validação

```bash
# 6.1 - Latência de alerta (< 5s)
# Passo 1: Simular condição (máquina parada)
START=$(date +%s)
curl -X POST http://localhost:8001/v1/telemetry/ingest \
  -d '{"machine_id":"TEST-ALERT","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","rpm":0,"feed_mm_min":0,"state":"stopped"}'

# Passo 2: Aguardar alerta no Slack (manual)
# Passo 3: Calcular latência
END=$(date +%s)
LATENCY=$((END - START))
echo "Latência: ${LATENCY}s"
# Esperado: < 5s

# 6.2 - Dedupe (máx 1 alerta/min)
# Simular condição repetida
for i in {1..10}; do
  curl -X POST http://localhost:8001/v1/telemetry/ingest \
    -d '{"machine_id":"TEST-DEDUPE","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","rpm":0,"feed_mm_min":0,"state":"stopped"}'
  sleep 10
done

# Verificar logs Celery (deve ter apenas 1 alerta enviado)
grep "TEST-DEDUPE" celery.log | grep "Alerta enviado" | wc -l
# Esperado: 1

# 6.3 - Slack delivery rate
# Verificar Celery logs
grep "Alerta enviado para Slack" celery.log | tail -20
# Todos devem ter "Status: 200 OK"

# 6.4 - Falsos positivos (manual)
# Revisar todos os alertas enviados nas últimas 24h
# Classificar cada um como TP (true positive) ou FP (false positive)
# Taxa FP deve ser 0%

# 6.5 - Cobertura de regras
grep -c "^  - name:" config/alerts.yaml
# Esperado: >= 3
```

### Evidências Requeridas
- [ ] Timestamp de condição + timestamp de alerta (diff < 5s)
- [ ] Celery logs mostrando dedupe
- [ ] Screenshots de Slack (3+ alertas diferentes)
- [ ] Análise de falsos positivos (0 em 24h)
- [ ] `alerts.yaml` com ≥ 3 regras

---

## Gate 7: Multi-Máquina (10 CNCs)

### Critérios de Aceite
| # | Critério | Target | Comando de Validação |
|---|----------|--------|----------------------|
| 7.1 | Concorrência | 10 máquinas | Config YAML |
| 7.2 | Perda de dados | < 0.5% | SQL count |
| 7.3 | Latência P95 ingest | < 2s | OpenTelemetry |
| 7.4 | Isolamento de falha | 1 máquina down = 0 impacto | Kill test |
| 7.5 | Dashboard render | < 1s | Browser DevTools |

### Comandos de Validação

```bash
# 7.1 - Subir 10 simuladores
for i in {5000..5009}; do
  python3 scripts/mtconnect_simulator.py --port $i &
  echo "Simulador $((i-4999)) rodando na porta $i"
done

# Verificar todos ativos
for i in {5000..5009}; do
  curl -s http://localhost:$i/health || echo "Porta $i FALHOU"
done

# 7.2 - Perda de dados (< 0.5%)
# Executar adapter por 1 hora
timeout 3600 python3 backend/mtconnect_adapter.py --config config/machines.yaml

# Verificar contagem
psql -U cnc_user -d cnc_telemetry -c "
  SELECT 
    machine_id,
    COUNT(*) AS actual_samples,
    1800 AS expected_samples,  -- 1 sample/2s * 3600s / 2
    ROUND((1 - COUNT(*)::numeric / 1800) * 100, 2) AS loss_pct
  FROM telemetry
  WHERE ts > NOW() - INTERVAL '1 hour'
  GROUP BY machine_id
  ORDER BY loss_pct DESC;
"
# Todas as máquinas: loss_pct < 0.5%

# 7.3 - Latência P95 ingest
# Usar OpenTelemetry + Prometheus
curl http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket{handler=\"/v1/telemetry/ingest\"}[5m]))
# Resultado < 2.0

# 7.4 - Isolamento de falha
# Matar 1 simulador
kill -9 $(lsof -ti :5005)

# Aguardar 2 minutos
sleep 120

# Verificar outras máquinas continuam funcionando
psql -U cnc_user -d cnc_telemetry -c "
  SELECT 
    machine_id,
    MAX(ts) AS last_sample
  FROM telemetry
  GROUP BY machine_id
  HAVING MAX(ts) > NOW() - INTERVAL '10 seconds'
  ORDER BY machine_id;
"
# Deve mostrar 9 máquinas (exceto CNC-SIM-006)

# 7.5 - Dashboard render time
# Abrir Chrome DevTools > Network > Throttling: Fast 3G
# Medir tempo até DOM loaded
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5173/fleet

# curl-format.txt:
# time_total: %{time_total}s
# Esperado: < 1.0s
```

### Evidências Requeridas
- [ ] `machines.yaml` com 10 entradas
- [ ] SQL query mostrando perda < 0.5% para todas
- [ ] OpenTelemetry metrics (P95 < 2s)
- [ ] Log de teste de falha (9/10 máquinas continuaram)
- [ ] Chrome DevTools screenshot (render < 1s)

---

## Gate 8: OEE Básico

### Critérios de Aceite
| # | Critério | Target | Validação |
|---|----------|--------|-----------|
| 8.1 | Cálculo OEE | A × P × Q | SQL query |
| 8.2 | Granularidade | Turno/Dia | API endpoint |
| 8.3 | Dashboard card | OEE visual | Screenshot |
| 8.4 | Query latency | < 500ms | EXPLAIN ANALYZE |

### Comandos de Validação

```sql
-- 8.1 - Cálculo OEE
SELECT 
  machine_id,
  date,
  availability,
  performance,
  quality,
  (availability * performance * quality) AS oee
FROM oee_daily
WHERE date = CURRENT_DATE - 1
  AND machine_id = 'ABR-850';
-- oee entre 0.0 e 1.0

-- 8.2 - API endpoint
curl "http://localhost:8001/v1/machines/ABR-850/oee?date=2025-11-04" | jq
# Retorna: availability, performance, quality, oee

-- 8.4 - Query latency
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM oee_daily
WHERE machine_id = 'ABR-850'
  AND date BETWEEN '2025-10-01' AND '2025-11-05';
-- Execution Time < 500ms
```

---

## Resumo de SLOs

| Métrica | SLO Q4'25 | SLO Q1'26 | Medição |
|---------|-----------|-----------|---------|
| **Availability** | 99.0% | 99.5% | Uptime monitoring |
| **Latency P95 /ingest** | < 2s | < 1s | OpenTelemetry |
| **Latency P99 /ingest** | < 5s | < 3s | OpenTelemetry |
| **Data Loss** | < 0.5% | < 0.1% | SQL audit |
| **Alert Latency** | < 5s | < 3s | Manual timing |
| **Query 30d History** | < 2s | < 1s | `time curl` |

---

**Princípio:** Meça tudo. Se não pode medir, não pode melhorar.

**Tooling:**
- PostgreSQL: `EXPLAIN ANALYZE`, `pg_stat_statements`
- OpenTelemetry: Traces, Metrics
- Prometheus: SLO dashboards
- Grafana: Visualização
- cURL: Load testing
- Apache Bench: Concorrência

---

**Próxima Revisão:** Após cada gate PASS
