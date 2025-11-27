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
