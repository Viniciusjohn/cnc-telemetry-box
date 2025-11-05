# 🎯 Próximos Passos Imediatos

**Data:** 2025-11-05  
**Status Atual:** F3 ✅ PASS, F4 🔜 Em execução

---

## 🔥 Esta Semana (5-10 Nov)

### 1. ✅ Finalizar Gate F3
- [x] Dashboard PWA funcionando
- [x] Todos os serviços rodando
- [ ] Executar `./scripts/gate_f3.sh` completo
- [ ] Capturar screenshots (desktop + mobile)
- [ ] Preencher `docs/F3_GATE_UNICO_*.md`
- [ ] Anexar relatório na Issue #4

### 2. 🚀 Executar F4 Piloto de Campo
- [ ] Contatar Nestor (email em `docs/email_novatech.md`)
- [ ] Agendar janela de 2h
- [ ] Obter: Série, IP, Porta, MTConnect version
- [ ] Executar scripts de campo
- [ ] Monitorar soak test 2h
- [ ] Coletar métricas (perda, latência, uptime)

**Deadline:** Sexta 10/Nov

---

## 📅 Próximos 30 Dias (Nov-Dez)

### Semana 1-2 (11-24 Nov)

#### F5: Persistência PostgreSQL
**Objetivo:** Habilitar histórico de telemetria

**Tasks:**
- [ ] Instalar PostgreSQL + TimescaleDB
- [ ] Criar schema `telemetry_samples` (hypertable)
- [ ] Migration com Alembic
- [ ] Modificar `/ingest` para salvar em DB
- [ ] Endpoint `/v1/machines/{id}/history?from=X&to=Y`
- [ ] Testes de retenção (30 dias)

**Estimativa:** 1.5 semanas  
**Critério de Aceite:**
- ✅ Query 30 dias de dados < 2s
- ✅ Ingest throughput > 100 samples/s
- ✅ Backup automático diário

---

#### F6: Sistema de Alertas
**Objetivo:** Notificações proativas

**Tasks:**
- [ ] Schema de regras de alerta (YAML)
- [ ] Engine de avaliação (Celery worker)
- [ ] Webhook genérico (POST com payload JSON)
- [ ] Integração Slack (incoming webhooks)
- [ ] Dashboard de alertas ativos
- [ ] Dedupe de alertas (evitar spam)

**Exemplo de Regra:**
```yaml
alerts:
  - name: machine_stopped_long
    condition: state == 'stopped' AND duration > 600  # 10min
    severity: warning
    channels:
      - type: slack
        webhook: https://hooks.slack.com/services/xxx
      - type: webhook
        url: https://api.cliente.com/alerts
```

**Estimativa:** 1.5 semanas  
**Critério de Aceite:**
- ✅ Alerta dispara < 30s após condição
- ✅ Slack recebe mensagem formatada
- ✅ Zero falsos positivos em 24h

---

### Semana 3-4 (25 Nov - 8 Dez)

#### F7: Multi-Máquina
**Objetivo:** Monitorar múltiplos CNCs simultaneamente

**Tasks:**
- [ ] Adapter suporta lista de máquinas (config YAML)
- [ ] Thread pool (1 thread por máquina)
- [ ] Dashboard: Lista de máquinas
- [ ] Filtros: estado, planta, modelo
- [ ] Endpoint `/v1/fleet/summary`
- [ ] Card de agregação (OEE médio, uptime total)

**Estimativa:** 2 semanas  
**Critério de Aceite:**
- ✅ 10 máquinas simultâneas sem degradação
- ✅ Falha em 1 máquina não afeta outras
- ✅ Dashboard renderiza < 1s com 10 máquinas

---

## 🎯 Q1 2026 (Jan-Mar)

### Janeiro
- **F8:** Analytics Dashboard (OEE, trends, heatmaps)
- **F9 (parte 1):** Research OPC-UA (asyncua PoC)

### Fevereiro
- **F9 (parte 2):** OPC-UA adapter completo
- **F10 (parte 1):** Dataset collection para ML

### Março
- **F10 (parte 2):** Modelo de Anomaly Detection (Isolation Forest)
- **Beta Clientes:** 3 early adopters

---

## 💰 Monetização (Mar 2026)

### Preparação
- [ ] Criar landing page (Next.js + TailwindCSS)
- [ ] Definir pricing tiers:
  - Free: 1 máquina, 7 dias histórico
  - Pro: $99/máquina/mês, 90 dias, alertas
  - Enterprise: Custom, SLA 99.9%
- [ ] Integrar Stripe (pagamento)
- [ ] Sistema de trial (14 dias)
- [ ] Onboarding self-service

---

## 📊 Métricas para Acompanhar

### Técnicas (Semanais)
- Uptime dos serviços (target: 99.9%)
- Latência E2E P99 (target: < 5s)
- Perda de dados (target: < 0.1%)
- Cobertura de testes (target: > 80%)

### Negócio (Mensais)
- Máquinas monitoradas (atual: 1, meta Q1: 10)
- Clientes ativos (atual: 0, meta Q1: 3)
- MRR (Monthly Recurring Revenue)
- Churn rate (meta: < 5%)

---

## 🚧 Riscos e Contingências

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| F4 Piloto falha | Alto | Ter backup de outra máquina testada |
| PostgreSQL performance | Médio | Usar índices, particionamento, read replicas |
| Delay em OPC-UA | Baixo | Focar em MTConnect primeiro, OPC-UA é nice-to-have |
| Falta de clientes beta | Alto | Networking agressivo, LinkedIn outreach, feiras |

---

## 📞 Contatos Importantes

### Clientes Potenciais
- **Novatech (Nestor):** Piloto F4 em andamento
- **[Adicionar outros]**

### Parceiros Técnicos
- **MTConnect Institute:** Certificação futura
- **OPC Foundation:** Compliance OPC-UA

### Eventos
- **FEIMEC 2026:** Maio (São Paulo)
- **CIMATRON 2026:** Agosto (São Paulo)

---

## 🎓 Aprendizado Contínuo

### Cursos/Certificações (Prioridade)
1. **TimescaleDB Time-Series:** https://www.timescale.com/learn
2. **FastAPI Advanced Patterns:** https://fastapi.tiangolo.com/advanced/
3. **PostgreSQL Performance Tuning:** Use the Index, Luke!
4. **MLOps Fundamentals:** Coursera/DataTalks.Club

### Livros
- "Designing Data-Intensive Applications" (Martin Kleppmann)
- "The DevOps Handbook" (Gene Kim)
- "Building Microservices" (Sam Newman)

---

## ✅ Checklist Semanal

### Segunda-feira
- [ ] Review de métricas da semana passada
- [ ] Planejar sprints (Notion/Trello)
- [ ] Atualizar roadmap se necessário

### Quarta-feira
- [ ] Mid-week check-in
- [ ] Resolver blockers

### Sexta-feira
- [ ] Deploy em staging
- [ ] Retrospectiva
- [ ] Commit e push código
- [ ] Atualizar docs

---

**🎯 Foco desta semana:** Finalizar F3 Gate + Iniciar F4 Piloto  
**📅 Próxima revisão:** 12/Nov (Segunda)  
**🚀 Meta do mês:** F5 + F6 em produção
