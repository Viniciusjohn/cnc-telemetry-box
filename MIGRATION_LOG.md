# Migration Log - CNC Telemetry Box

## 2025-11-27 - Micro-experimento

**Windows ref**: commit atual (simulado)  
**Descrição**: Adicionar campo `box_version: "1.0"` ao endpoint `/box/healthz`  
**Arquivos alterados**:
- `backend/app/routers/box_health.py` (linha 110: adicionado `box_version`)
- `backend/app/routers/box_health.py` (linha 13: import `text` do sqlalchemy)
- `backend/app/routers/box_health.py` (linha 24: `conn.execute(text("SELECT 1"))`)

**Testes executados**:
- ✅ Import da função funciona
- ✅ Health check retorna `box_version: 1.0`
- ✅ Status geral: `healthy`

**Resultado**: SUCCESS  
**Tempo total**: 00:02 - 00:07 (5 minutos, incluindo instalação deps)  
**Fricções**: SQLAlchemy v2 exige `text()` para raw SQL (bug pré-existente)
