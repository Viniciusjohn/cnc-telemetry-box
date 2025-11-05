# ORIENTAÇÕES DE CONFIGURAÇÃO — cnc-telemetry

**Documento de Planejamento — NÃO EXECUTADO**  
**Data:** 2025-11-05  
**Modo:** Planejar apenas, não aplicar mudanças

---

## 📋 RESUMO EXECUTIVO

Configuração moderna do Cursor para **cnc-telemetry** (sistema de telemetria CNC Mobile+PC) com:
- Cursor Rules em `.cursor/rules/` (não `.cursorrules` legado)
- Isolamento completo do CNC-Genius
- MCP Server global opcional
- Gates de verificação

**Stack:** TypeScript/React/Vite + FastAPI + PWA + Playwright

---

## 🎯 ESCOPO DO PROJETO

### Métricas Coletadas
- RPM (rotação spindle)
- Feed (mm/min)
- Estado: Running/Stopped (regra ≥15s)
- Tempo de usinagem

### Headers Obrigatórios
```http
X-Contract-Fingerprint: 010191590cf1
X-Request-Id: <uuid-v4>
Cache-Control: no-store
Vary: Origin
Server-Timing: total;dur=<ms>
```

### Requisitos
- Lighthouse ≥90
- Polling 2s
- PWA instalável

---

## 📁 ESTRUTURA DE ARQUIVOS

### Comandos Sugeridos (NÃO EXECUTAR)

```bash
# 1. Criar estrutura de rules
mkdir -p .cursor/rules

# 2. Criar arquivos (usar conteúdo das seções abaixo)
touch .cursor/rules/000_base.md
touch .cursor/rules/010_api.md
touch .cursor/rules/020_ui.md
touch .cursor/rules/030_adapter.md
```

---

## 📄 CONTEÚDO DOS ARQUIVOS

### 1. `.cursor/rules/000_base.md`

**Propósito:** Regras base, proibições, stack, modo do agente

**Conteúdo:**
```markdown
# Base Rules — cnc-telemetry

## Escopo
Sistema de telemetria CNC: RPM, Feed (mm/min), Running/Stopped (≥15s), Tempo de usinagem.

## 🚫 PROIBIÇÕES — Termo-Ban: CNC-Genius
NÃO referenciar, importar ou mencionar:
- CNC-Genius
- Políticas/prompts/código de projetos anteriores

Validação: Rejeitar qualquer menção a "CNC-Genius".

## Stack
Frontend: TypeScript 5.x, React 18.x, Vite 5.x, Playwright
Backend: FastAPI 0.100+, Python 3.11+

## Headers Obrigatórios
X-Contract-Fingerprint: 010191590cf1
X-Request-Id: <uuid-v4>
Cache-Control: no-store
Vary: Origin
Server-Timing: total;dur=<ms>

## Modo de Operação do Agente
1. Planejar antes de executar
2. Aguardar comando "executar" ou "aplicar"
3. Não criar scaffolds sem aprovação

## Estilo de Código
- TypeScript: Componentes funcionais + hooks
- FastAPI: Type hints, async, response_model

## Performance
- Lighthouse ≥90 (todas as categorias)
- FCP < 1.8s, TTI < 3.8s, CLS < 0.1
```

---

### 2. `.cursor/rules/010_api.md`

**Propósito:** Contratos de API, regras de negócio

**Conteúdo:**
```markdown
# API Contracts — cnc-telemetry

## Endpoints

### POST /v1/telemetry/ingest
Request: { machine_id, timestamp, rpm, feed_mm_min, state }
Response (201): { ingested, session_id, timestamp }

### GET /v1/machines/{id}/status
Query: ?window_sec=60
Response: { machine_id, current_state, rpm, feed_mm_min, session {...}, last_update }

### GET /v1/machines/status?view=grid
Query: view=grid|operator|wall
Response: { view, machines: [...], last_update }

## Regras de Negócio

### Estado Running/Stopped (≥15s)
- current_rpm > 0 E duration ≥15s → "running"
- current_rpm == 0 E duration ≥15s → "stopped"
- Caso contrário → manter estado anterior

### Sessões
- Início: Primeiro "running" após ≥15s stopped
- Fim: Primeiro "stopped" após ≥15s running
- session_id: UUID gerado no início

### CORS
Permitir: http://localhost:5173, https://*.cnc-telemetry.local

FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["..."], ...)
```

## Validação
- Pydantic models
- Retornar 422 para erros de validação
```

---

### 3. `.cursor/rules/020_ui.md`

**Propósito:** PWA, rotas, componentes, testes

**Conteúdo:**
```markdown
# UI Rules — cnc-telemetry

## PWA
Manifest: public/manifest.json
Service Worker: Network-first para API, cache-first para assets

## Rotas
/dashboard?view=operator → Layout responsivo
/dashboard?view=wall → Layout fullscreen (1920×1080)

## Polling
Intervalo: 2s
Pausar quando tab inativa (Page Visibility API)
Exponential backoff em caso de erro

## Componentes

### MachineCard
Props: machineId, state, rpm, feedMmMin, sessionDurationSec
Cores: 🟢 running, 🔴 stopped, 🟡 transitioning

### StatusGrid
Desktop: 3-4 colunas
Tablet: 2 colunas
Mobile: Lista vertical

## Performance (Lighthouse ≥90)
- FCP < 1.8s, LCP < 2.5s, TTI < 3.8s, TBT < 200ms, CLS < 0.1
- Code splitting, lazy loading, minificação

## Testes Playwright
Devices: iPhone 12, Desktop 1366×768

playwright.config.ts:
```typescript
projects: [
  { name: 'Mobile', use: { ...devices['iPhone 12'] } },
  { name: 'Desktop', use: { viewport: { width: 1366, height: 768 } } },
]
```

Tests: dashboard loads, polling updates, wall view

## Styling
TailwindCSS 3.x
Colors: cnc-running (#10b981), cnc-stopped (#ef4444), cnc-idle (#f59e0b)
Dark mode preferencial
```

---

### 4. `.cursor/rules/030_adapter.md`

**Propósito:** Integrações MTConnect e Mitsubishi

**Conteúdo:**
```markdown
# Adapter Rules — cnc-telemetry

## Rotas de Integração

### Rota A: MTConnect
Protocolo: HTTP REST (GET /current)
Mapeamento:
- Spindle/Speed → rpm
- Path/Feedrate/Actual → feed_mm_min
- Execution (ACTIVE→running, STOPPED→stopped, READY→idle)

Polling: 1s
Retry: Exponential backoff

### Rota B: SDK Mitsubishi (Edge)
Protocolo: FFI (.so/.dll)
Interface: mitsubishi_connect, mitsubishi_read_data, mitsubishi_disconnect

Deployment: Edge device (RPi4, mini-PC)
Envio: POST /v1/telemetry/ingest a cada 2s

## Interface Comum
```python
class TelemetryAdapter(ABC):
    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def read_telemetry(self) -> Dict[str, any]: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
```

## Registro de Adapters
ADAPTER_REGISTRY = { "mtconnect": MTConnectAdapter, "mitsubishi": MitsubishiAdapter }

## Configuração
machines.yaml: machine_id, adapter type, config (base_url ou ip_address)

## Gerenciamento de Estado (≥15s)
StateManager: buffer de 15s, verifica homogeneidade, transição confirmada
```

---

## 🔧 CONFIGURAÇÃO MCP (Opcional)

### Localização
`~/.cursor/mcp.json` (global, não workspace)

### Conteúdo Proposto

```json
{
  "mcpServers": {
    "cnc-telemetry-docs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/viniciusjohn/iot/docs"],
      "env": {
        "MCP_SERVER_NAME": "cnc-telemetry-docs"
      }
    }
  }
}
```

### Instruções de Ativação

**Via Settings UI (recomendado):**
1. Abrir Cursor
2. Menu: **Settings** → **Developer** → **MCP Tools**
3. Clicar **Add Server**
4. Preencher:
   - **Name:** cnc-telemetry-docs
   - **Command:** npx
   - **Args:** -y, @modelcontextprotocol/server-filesystem, /home/viniciusjohn/iot/docs
5. Salvar e reiniciar Cursor
6. Validar: Verificar "MCP Tools" mostrando server ativo

**Via arquivo (alternativa):**
```bash
# Criar/editar ~/.cursor/mcp.json
cat > ~/.cursor/mcp.json << 'EOF'
{
  "mcpServers": {
    "cnc-telemetry-docs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/viniciusjohn/iot/docs"]
    }
  }
}
EOF
```

---

## ✅ GATES DE VERIFICAÇÃO

### Gate R1: Isolamento de Rules
**Validação:** Ao abrir este repo, Cursor carrega APENAS `.cursor/rules/*` deste projeto.

**Como verificar:**
1. Abrir `/home/viniciusjohn/iot` no Cursor
2. Perguntar ao Cursor: "Quais são as regras ativas?"
3. Confirmar resposta menciona apenas `000_base.md`, `010_api.md`, `020_ui.md`, `030_adapter.md`
4. Confirmar ausência de referências a `.cursorrules` ou outros projetos

### Gate R2: Termo-Ban CNC-Genius
**Validação:** Nenhuma menção a CNC-Genius nas rules; termo explicitamente proibido.

**Como verificar:**
```bash
# Buscar "CNC-Genius" nas rules (deve retornar apenas proibição)
grep -r "CNC-Genius" .cursor/rules/
# Resultado esperado: apenas em 000_base.md seção "PROIBIÇÕES"
```

### Gate R3: Checklist PWA e Headers
**Validação:** Backend implementa CORS e headers obrigatórios; frontend é PWA instalável.

**Checklist (para quando executar):**
- [ ] Backend retorna headers: X-Contract-Fingerprint, X-Request-Id, no-store, Vary, Server-Timing
- [ ] CORS configurado para http://localhost:5173
- [ ] public/manifest.json presente e válido
- [ ] Service Worker registrado
- [ ] Lighthouse PWA score ≥90

### Gate R4: MCP Ativo (opcional)
**Validação:** MCP server "cnc-telemetry-docs" listado e conectado.

**Como verificar:**
1. Cursor → Settings → Developer → MCP Tools
2. Verificar "cnc-telemetry-docs" com status ✅ Connected
3. Testar: Perguntar ao Cursor "Leia o arquivo docs/ORIENTACOES.md via MCP"

---

## 📚 DIFERENÇAS vs `.cursorrules` (Legado)

### Sistema Antigo: `.cursorrules`
- Arquivo único na raiz do projeto
- Formato: Markdown sem estrutura
- Limitação: Difícil organizar regras complexas
- Status: **Legado** (suportado mas não recomendado)

### Sistema Moderno: `.cursor/rules/`
- Diretório dedicado com múltiplos arquivos
- Formato: Markdown com prefixo numérico (ordem de carregamento)
- Vantagens:
  - **Modularidade:** Separar regras por domínio (base, api, ui, adapter)
  - **Ordem controlada:** 000_, 010_, 020_ definem precedência
  - **Escalabilidade:** Adicionar novas rules sem conflito
  - **Manutenibilidade:** Editar uma área sem afetar outras

### Exemplo de Migração
```bash
# Antigo (NÃO usar)
.cursorrules

# Novo (USAR)
.cursor/rules/000_base.md
.cursor/rules/010_api.md
.cursor/rules/020_ui.md
.cursor/rules/030_adapter.md
```

---

## 🚀 PASSO A PASSO PARA VALIDAÇÃO

### 1. Criar Estrutura de Rules

```bash
# Executar quando receber comando "executar"
mkdir -p .cursor/rules
cd .cursor/rules

# Criar arquivos (copiar conteúdo das seções acima)
cat > 000_base.md << 'EOF'
[copiar conteúdo da seção "1. .cursor/rules/000_base.md"]
EOF

cat > 010_api.md << 'EOF'
[copiar conteúdo da seção "2. .cursor/rules/010_api.md"]
EOF

cat > 020_ui.md << 'EOF'
[copiar conteúdo da seção "3. .cursor/rules/020_ui.md"]
EOF

cat > 030_adapter.md << 'EOF'
[copiar conteúdo da seção "4. .cursor/rules/030_adapter.md"]
EOF
```

### 2. Validar Carregamento das Rules

**Método 1: Via Cursor Chat**
1. Reabrir workspace no Cursor
2. Perguntar: "Quais são as regras de desenvolvimento deste projeto?"
3. Verificar resposta menciona: cnc-telemetry, proibição de CNC-Genius, stack TypeScript/React/FastAPI

**Método 2: Via Arquivo de Log**
```bash
# Cursor mantém logs de rules carregadas (localização varia)
# Verificar ~/.cursor/logs/ ou via Debug Console no Cursor
```

### 3. Configurar MCP (se desejado)

**Via UI:**
1. Cursor → Settings (⚙️) → Developer → MCP Tools
2. Clicar "Add Server"
3. Preencher campos:
   - Name: `cnc-telemetry-docs`
   - Command: `npx`
   - Args (um por linha):
     ```
     -y
     @modelcontextprotocol/server-filesystem
     /home/viniciusjohn/iot/docs
     ```
4. Salvar
5. Reiniciar Cursor
6. Retornar a MCP Tools e verificar status "Connected"

**Via arquivo:**
```bash
# Editar ~/.cursor/mcp.json
nano ~/.cursor/mcp.json

# Adicionar conteúdo da seção "CONFIGURAÇÃO MCP"
# Salvar e reiniciar Cursor
```

### 4. Executar Gates de Verificação

**Gate R1 (Isolamento):**
```bash
# Perguntar ao Cursor: "Mostre as regras ativas"
# Verificar output menciona apenas 000_base, 010_api, 020_ui, 030_adapter
```

**Gate R2 (Termo-Ban):**
```bash
grep -rn "CNC-Genius" .cursor/rules/
# Deve retornar apenas a linha de proibição em 000_base.md
```

**Gate R3 (PWA/Headers):**
```bash
# Executar após implementar backend/frontend
curl -I http://localhost:8000/v1/machines/status?view=grid
# Verificar headers: X-Contract-Fingerprint, X-Request-Id, etc.

npx lighthouse http://localhost:5173 --view
# Verificar PWA score ≥90
```

**Gate R4 (MCP):**
```bash
# No Cursor Chat, perguntar:
# "Use MCP para listar arquivos em docs/"
# Verificar resposta contém ORIENTACOES.md
```

---

## 📖 REFERÊNCIAS

### Documentação Oficial

1. **Cursor Rules (Sistema Moderno)**
   - URL: https://docs.cursor.com/context/rules-for-ai
   - Citação relevante: "We recommend using `.cursor/rules/` instead of `.cursorrules` for better organization."

2. **Using Agent in CLI**
   - URL: https://docs.cursor.com/agent/overview
   - Menciona: "Agent respects rules in `.cursor/rules/` directory with numeric prefixes for ordering."

3. **MCP em Cursor**
   - URL: https://docs.cursor.com/advanced/model-context-protocol
   - Instruções: Settings → Developer → MCP Tools

4. **MTConnect Standard**
   - URL: https://www.mtconnect.org/
   - Usado para adaptador Rota A

5. **FastAPI Documentation**
   - URL: https://fastapi.tiangolo.com/
   - Framework do backend

6. **Playwright Testing**
   - URL: https://playwright.dev/
   - Framework de testes E2E

---

## 🎯 PRÓXIMOS PASSOS (Aguardando Comando "Executar")

Quando receber autorização, executar na ordem:

1. **Criar estrutura de rules**
   ```bash
   mkdir -p .cursor/rules
   # Criar 4 arquivos .md com conteúdo proposto
   ```

2. **Validar carregamento**
   - Reabrir Cursor
   - Verificar regras ativas

3. **Configurar MCP (opcional)**
   - Via Settings UI ou ~/.cursor/mcp.json
   - Validar conexão

4. **Executar gates R1 e R2**
   - Confirmar isolamento e termo-ban

5. **Iniciar scaffold do projeto**
   - Backend FastAPI
   - Frontend React+Vite
   - Adapters (MTConnect, Mitsubishi)

6. **Implementar e validar gates R3 e R4**
   - PWA funcional
   - Headers e CORS corretos
   - MCP acessível

---

## ✨ RESUMO

Este documento planejou:
- ✅ Estrutura de 4 arquivos de rules em `.cursor/rules/`
- ✅ Conteúdo completo para cada arquivo (base, api, ui, adapter)
- ✅ Configuração opcional de MCP global
- ✅ 4 gates de verificação (R1-R4)
- ✅ Diferenças vs `.cursorrules` legado
- ✅ Passo a passo de validação
- ✅ Referências a documentação oficial

**Status:** PLANEJAMENTO CONCLUÍDO. Aguardando comando "executar" para aplicar mudanças.

**Termo-Ban Ativo:** CNC-Genius (não referenciar em nenhum artefato)

**Workspace:** `/home/viniciusjohn/iot` (atualmente vazio)
