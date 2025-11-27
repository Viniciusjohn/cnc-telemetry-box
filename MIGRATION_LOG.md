# Migration Log - CNC Telemetry Box

## Padrão de Commits
- **fix**: correções de bugs/infra (ex.: `fix: sqlalchemy v2 text() wrapper`)
- **migrate**: features migradas do Windows (ex.: `migrate: add box_version from windows@<hash>`)

## Checklist Pré-Migração
1. Dependências instaladas: `pip install -r backend/requirements.txt`
2. Box no latest main: `git checkout main && git pull`
3. Branch limpo: `git status`
4. Healthz baseline: `curl http://localhost:8001/box/healthz`
5. Hash Windows anotado: `git rev-parse HEAD`

## Tempo Esperado por Etapa (baseline)
- Dependências: 3 min
- Diff/análise: 1 min  
- Portar lógica: 2 min
- Testes: 2 min
- Commits: 1 min
- **Total esperado**: ≤ 15 min (mudanças médias)

---

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
**Commits**: 1 commit agrupado (deveria ser 2 separados)  
**Rollback**: ✅ Funcionou via `git checkout HEAD~1`

---

## 2025-11-27 - Segundo Experimento (db_status + machine_count)

**Windows ref**: a3a6fb86c2c2d8fed00565269be712ff3ab3e3e7  
**Descrição**: Adicionar campos `db_status` e `machine_count` ao endpoint `/box/healthz`  
**Arquivos alterados**:
- `backend/app/routers/box_health.py` (+108 linhas)
  - Função `get_db_status()` com detecção de dialeto SQLite/PostgreSQL
  - Função `get_machine_count()` com DISTINCT queries
  - Integração dos novos campos no response JSON

**Testes executados**:
- ✅ Healthz retorna `db_status: connected` (dialect: sqlite)
- ✅ Healthz retorna `machine_count: {total_machines: 5, telemetry_machines: 5, status_machines: 0}`
- ✅ Campos `db_status` e `machine_count` presentes no JSON
- ✅ Rollback validado: campos removidos após `git checkout HEAD~1`

**Resultado**: SUCCESS  
**Tempo total**: 8 minutos (vs meta ≤ 15 min)  
**Tempo por etapa**:
- Checklist: 1 min
- Implementação: 4 min
- Testes/Debug: 2 min  
- Commit: 1 min

**Fricções**: 
- Detectar SQLite vs PostgreSQL exigiu branch SQL (resolvido com `engine.dialect.name`)
- Nenhuma dependência adicional necessária

**Commits**: ✅ 1 commit separado (padrão migrate: from windows@hash)  
**Rollback**: ✅ Funcionou perfeitamente (campos sumiram/apareceram)  
**Checklist**: ✅ 5/5 itens executados

**Conclusão**: Workflow v2 validado para mudanças médias - tempo ≤ 15 min, commits separados, rollback funcional
