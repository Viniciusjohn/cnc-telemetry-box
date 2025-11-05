# ⚡ Executar F3 — Guia Rápido

**Objetivo:** Validar Dashboard PWA (F3) localmente antes do campo

**Tempo estimado:** 15 minutos

---

## 🚀 Passo 1: Iniciar Serviços (3 terminais)

### Terminal 1 - Simulador MTConnect
```bash
cd /home/viniciusjohn/iot
python3 scripts/mtconnect_simulator.py --port 5000
```

**Saída esperada:**
```
🚀 MTConnect Agent Simulator rodando em http://0.0.0.0:5000
   Endpoints: /probe, /current, /sample
```

---

### Terminal 2 - Backend API
```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate
uvicorn app:app --port 8001 --reload
```

**Saída esperada:**
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

---

### Terminal 3 - Adapter (Popular Dados)
```bash
cd /home/viniciusjohn/iot/backend
source .venv/bin/activate

# Executar por 1-2 minutos para popular dados
timeout 120 python3 mtconnect_adapter.py || true
```

**Saída esperada:**
```
🔌 Conectando ao MTConnect Agent: http://localhost:5000
✅ #1 | RPM=4200.5 Feed=1250.0 State=running Seq=12345
✅ #2 | RPM=4180.2 Feed=1245.5 State=running Seq=12365
...
```

---

## 🧪 Passo 2: Smoke Tests Automatizados

### Executar Script

```bash
cd /home/viniciusjohn/iot
chmod +x scripts/smoke_f3.sh
./scripts/smoke_f3.sh
```

**Saída esperada:**
```
🧪 F3 Smoke Tests
════════════════════════════════════════
API: http://localhost:8001
Agent: http://localhost:5000
Machine: CNC-SIM-001

1️⃣  Testando headers canônicos...
✅ PASS - Cache-Control: no-store presente
✅ PASS - Vary presente
✅ PASS - X-Contract-Fingerprint presente
✅ PASS - Server-Timing presente

2️⃣  Testando contrato JSON...
✅ PASS - Campo 'rpm' válido (≥0)
✅ PASS - Campo 'feed_mm_min' válido (≥0)
✅ PASS - Campo 'state' normalizado
✅ PASS - Campo 'updated_at' presente

...

════════════════════════════════════════
📊 RESUMO
════════════════════════════════════════
✅ PASS: 15
❌ FAIL: 0

🎉 Todos os testes passaram!
```

---

## 🖥️ Passo 3: Validar UI

### Terminal 4 - Frontend
```bash
cd /home/viniciusjohn/iot/frontend
npm run dev
```

**Saída esperada:**
```
  VITE ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### Abrir no Navegador
```
http://localhost:5173
```

### Checklist Visual

- [ ] **Header** "CNC Telemetry — Dashboard" aparece
- [ ] **Machine ID** "CNC-SIM-001" no canto superior direito
- [ ] **4 cards** visíveis:
  - RPM (rev/min)
  - Feed (mm/min)
  - Estado (RODANDO/PARADA/OCIOSA)
  - Atualizado (HH:MM:SS)
- [ ] **Valores atualizam** a cada ~2s
- [ ] **Cores corretas:**
  - 🟢 Verde se RODANDO
  - 🔴 Vermelho se PARADA
  - 🟡 Amarelo se OCIOSA
- [ ] **Footer** mostra "Polling: 2s | API: http://localhost:8001"
- [ ] **Console do navegador** sem erros (F12 → Console)

### Screenshot

**Desktop:**
```bash
# Capturar screenshot manualmente ou via ferramenta
```

**Mobile (simular):**
```
F12 → Toggle Device Toolbar (Ctrl+Shift+M)
Selecionar "iPhone 12 Pro" ou similar
```

---

## 🎭 Passo 4: Playwright E2E

### Executar Testes

```bash
cd /home/viniciusjohn/iot/frontend
npx playwright test e2e/status.spec.ts --reporter=list
```

**Saída esperada:**
```
Running 4 tests using 1 worker

  ✓  1 Dashboard F3 › deve exibir header e machine_id (2s)
  ✓  2 Dashboard F3 › deve exibir 4 cards de status (1s)
  ✓  3 Dashboard F3 › cards devem atualizar após 2s (polling) (3s)
  ✓  4 Dashboard F3 › deve exibir erro se backend não disponível (1s)

  4 passed (7s)
```

### Se Falhar

**Instalar dependências:**
```bash
cd frontend
npx playwright install
```

**Executar com UI (debug):**
```bash
npx playwright test e2e/status.spec.ts --ui
```

---

## 📊 Passo 5: Preencher Relatório

### Abrir Template

```bash
nano /home/viniciusjohn/iot/docs/F3_VALIDACAO.md
```

### Preencher Campos

1. **Resultados dos smoke tests** (colar saídas dos comandos)
2. **Screenshots** (desktop + mobile)
3. **Resultado Playwright** (colar saída)
4. **Marcar checkboxes** (✅ ou ❌)

### Exemplo de Preenchimento

```markdown
| # | Teste | Status | Observação |
|---|-------|--------|------------|
| 1 | Headers canônicos | ✅ | Cache-Control, Vary, Fingerprint, Server-Timing presentes |
| 2 | Contrato JSON | ✅ | Schema válido |
| 3 | Preflight 204 | ✅ | OPTIONS sem corpo, CORS OK |
| 4 | MTConnect /current | ✅ | RotaryVelocity, PathFeedrate, Execution |
| 5 | MTConnect /sample | ✅ | nextSequence=12345, monótona |
| 6 | Unidades corretas | ✅ | mm/s → mm/min (14.5 → 870.0) |
| 7 | UI Dashboard | ✅ | 4 cards, polling 2s, cores OK |
| 8 | Playwright E2E | ✅ | 4/4 PASS |
```

---

## 📎 Passo 6: Anexar na Issue #4

### Commit Relatório

```bash
cd /home/viniciusjohn/iot
git add docs/F3_VALIDACAO.md
git commit -m "F3 Validação: Smoke tests PASS (15/15), UI funcional, Playwright 4/4"
git push origin main
```

### Anexar na Issue

```bash
gh issue comment 4 -R Viniciusjohn/cnc-telemetry --body-file docs/F3_VALIDACAO.md
```

**Ou manualmente:**
1. Abrir https://github.com/Viniciusjohn/cnc-telemetry/issues/4
2. Colar conteúdo de `docs/F3_VALIDACAO.md`
3. Anexar screenshots

---

## ✅ Critérios de Aceite F3

| Critério | Meta | Como Validar |
|----------|------|--------------|
| **Smoke tests** | 15/15 PASS | `./scripts/smoke_f3.sh` |
| **UI funcional** | Polling 2s | Observar timestamp mudando |
| **Playwright** | 4/4 PASS | `npx playwright test` |
| **Headers** | 4/4 presentes | Script smoke |
| **CORS** | Preflight 204 | Script smoke |
| **MTConnect** | Sequência válida | Script smoke |

---

## 🎯 Próximos Passos (Após F3 PASS)

### 1. Enviar Email para Nestor

```bash
# Revisar template
cat /home/viniciusjohn/iot/docs/email_novatech.md

# Enviar com informações personalizadas
```

**Solicitar:**
- Série da máquina (M70/M700/M80/M800)
- IP e porta do MTConnect Agent
- Janela de 2h para testes

---

### 2. Preparar para Campo (F4)

```bash
# Revisar planejamento
cat /home/viniciusjohn/iot/docs/F4_PLANEJAMENTO.md

# Scripts que serão usados no campo:
ls -lh scripts/discover_agent.sh
ls -lh scripts/field_soak_30m.sh
ls -lh scripts/attach_report.sh
```

---

### 3. Aguardar Confirmação

- [ ] Nestor confirma série/IP
- [ ] Janela agendada (data/hora)
- [ ] Ambiente preparado (Agent rodando)
- [ ] Executar F4 no campo

---

## 🆘 Troubleshooting

### Backend não inicia

```bash
# Verificar porta ocupada
lsof -i :8001

# Matar processo
kill -9 <PID>

# Reinstalar dependências
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Frontend não compila

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

### Playwright falha

```bash
cd frontend
npx playwright install
npx playwright install-deps
```

---

### MTConnect Agent não responde

```bash
# Verificar se está rodando
curl -s http://localhost:5000/probe | head

# Reiniciar simulador
python3 scripts/mtconnect_simulator.py --port 5000
```

---

## 📞 Suporte

**Documentação:**
- F2 Soak: `docs/F2_RELATORIO_SOAK_30MIN.md`
- F3 Planejamento: `docs/F3_PLANEJAMENTO.md`
- F4 Planejamento: `docs/F4_PLANEJAMENTO.md`
- MTConnect Compliance: `docs/MTConnect_COMPLIANCE.md`

**Repositório:**
- https://github.com/Viniciusjohn/cnc-telemetry

---

**⚡ Tempo total estimado: 15 minutos**

**🎯 Ao concluir com sucesso, F3 estará PASS e pronto para campo!**
