# MM01 – Mapeamento de APIs de status/telemetria (backend)

Documentação rápida do que já existe hoje em `backend/app/routers/status.py` e rotas relacionadas.

## Endpoints encontrados

### 1. GET /v1/machines/{machine_id}/status

- **Descrição:** Retorna último status válido da máquina.
- **Headers canônicos:**
  - Cache-Control: no-store
  - Vary: Origin, Accept-Encoding
  - X-Contract-Fingerprint: 010191590cf1
  - Server-Timing: app;dur=<ms>
- **Resposta (MachineStatus):**
```json
{
  "machine_id": "SIM_M80_01",
  "controller_family": "MITSUBISHI_M8X",
  "timestamp_utc": "2025-11-13T10:00:00Z",
  "mode": "AUTOMATIC",
  "execution": "EXECUTING",
  "rpm": 3500,
  "feed_rate": 1200,
  "spindle_load_pct": 52,
  "tool_id": "T03",
  "alarm_code": null,
  "alarm_message": null,
  "part_count": 145,
  "update_interval_ms": 1000,
  "source": "mtconnect:sim"
}
```
- **Fallback:** Se não houver dados, devolve um status “idle” com valores default.

### 2. GET /v1/machines/{machine_id}/events

- **Descrição:** Retorna histórico de eventos da máquina (v0.2).
- **Query:** `limit` (padrão 50, máximo 200).
- **Resposta (MachineEvent[]):**
```json
[
  {
    "timestamp_utc": "2025-11-13T10:00:00Z",
    "execution": "EXECUTING",
    "mode": "AUTOMATIC",
    "rpm": 3500,
    "feed_rate": 1200,
    "spindle_load_pct": 52,
    "tool_id": "T03",
    "alarm_code": null,
    "alarm_message": null,
    "part_count": 145
  }
]
```

### 3. POST /v1/telemetry/ingest

- **Descrição:** Ingerir telemetria de uma máquina (idempotência por machine_id+timestamp).
- **Payload:**
```json
{
  "machine_id": "M80-DEMO-01",
  "timestamp": "2025-11-26T06:09:01Z",
  "rpm": 1500,
  "feed_mm_min": 800,
  "state": "running"
}
```
- **Ação:** Chama `status.update_status(...)` → atualiza `LAST_STATUS[machine_id]` e grava evento em `TelemetryEvents`.

### 4. GET /healthz

- **Descrição:** Healthcheck geral da API.
- **Resposta:**
```json
{
  "status": "ok",
  "service": "cnc-telemetry",
  "version": "v0.3",
  "worker_m80_enabled": true,
  "worker_consecutive_errors": 0
}
```

## Estrutura de status em memória

- **Variável:** `LAST_STATUS: Dict[str, MachineStatus]`
- **Atualização:** Sempre que `/v1/telemetry/ingest` recebe dados, `update_status` atualiza `LAST_STATUS[machine_id]`.
- **Uso:** `GET /v1/machines/{machine_id}/status` lê desse dicionário.

## O que falta (para multi-máquinas)

- **Endpoint de lista:** Não existe hoje um endpoint que retorne TODAS as máquinas conhecidas.
- **Endpoint de grid:** Não existe `GET /v1/machines/status?view=grid`.
- **Frontend:** Usa `MACHINE_ID` fixo (via `VITE_MACHINE_ID`), sem seletor.

## Próximos passos (MM02–MM09)

- Criar `GET /v1/machines` e `GET /v1/machines/status?view=grid` com base em `LAST_STATUS`.
- Adaptar frontend para usar estado global de máquinas e seletor.
- Validar com 2–3 máquinas fake via script de demo.
