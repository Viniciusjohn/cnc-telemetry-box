# 🚀 CNC Telemetry — Roadmap Estratégico de Produto
**Versão:** 1.0  
**Data:** 2025-11-05  
**Horizonte:** 6-24 meses  
**Status:** Draft para revisão executiva

---

## 📍 Posição Atual (Q4 2025)

### ✅ Conquistado
- **F2 PASS:** Adapter MTConnect com soak test 30min (0.22% perda)
- **F3 PASS:** Dashboard PWA com polling 2s em tempo real
- **Compliance MTConnect:** RotaryVelocity, PathFeedrate, Execution normalizado
- **Arquitetura validada:** Simulador → Adapter → API → Frontend
- **Tech Stack moderno:** Python/FastAPI + React/Vite + TypeScript

### 🔜 Em Andamento
- **F4:** Piloto de campo com Novatech ABR-850 (2h soak em produção)

---

## 🎯 Visão de Longo Prazo (18-24 meses)

**"Plataforma de telemetria industrial multi-protocolo com analytics preditivo e edge computing para chão de fábrica 4.0"**

### Pilares Estratégicos
1. **📊 Observabilidade Total:** Dashboard → Analytics → Alertas → ML
2. **🔌 Multi-Protocolo:** MTConnect → OPC-UA → Modbus → Proprietary
3. **☁️ Hybrid Cloud:** Edge + Cloud com sincronização eventual
4. **🤖 Inteligência:** Anomaly detection, predictive maintenance, OEE optimization
5. **🔐 Enterprise-Ready:** Multi-tenancy, RBAC, audit log, compliance

---

## 📅 Horizonte de Execução

### ⚡ Q4 2025 — Fundação Sólida (0-3 meses)

#### **F4: Piloto de Campo** ✅ *Em execução*
**Objetivo:** Validar sistema em ambiente produtivo real

**Entregas:**
- Adapter com persistência (instanceId + lastSequence em JSON)
- Script de descoberta automática (probe + validação)
- Monitoramento remoto via SSH + systemd
- Relatório de soak 2h com métricas reais
- Documentação operacional de campo

**Métricas de Aceite:**
- ✅ Perda de dados < 1% em 2h
- ✅ Latência E2E < 5s (P99)
- ✅ Adapter resiliente (auto-restart)
- ✅ Zero downtime do CNC durante deploy

---

#### **F5: Persistência + Histórico** 🆕
**Objetivo:** Habilitar análise histórica e auditoria

**Tech Stack:**
- PostgreSQL (TimescaleDB extension) para time-series
- Redis para cache de status hot
- Alembic para migrations
- SQLAlchemy ORM

**Entregas:**
- Schema otimizado para time-series (hypertables)
- Endpoint `/v1/machines/{id}/history?from=X&to=Y`
- Retenção configurável (30d default, 1y opcional)
- Indices em machine_id + timestamp
- Backfill script para dados existentes

**SQL Schema:**
```sql
CREATE TABLE telemetry_samples (
  id BIGSERIAL PRIMARY KEY,
  machine_id VARCHAR(50) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  rpm FLOAT NOT NULL CHECK (rpm >= 0),
  feed_mm_min FLOAT NOT NULL CHECK (feed_mm_min >= 0),
  state VARCHAR(20) NOT NULL CHECK (state IN ('running','stopped','idle')),
  sequence BIGINT,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_machine_time (machine_id, timestamp DESC)
);

SELECT create_hypertable('telemetry_samples', 'timestamp');
```

**Estimativa:** 2-3 semanas

---

#### **F6: Alertas + Notificações** 🆕
**Objetivo:** Proatividade operacional

**Features:**
- Alertas configuráveis (RPM > threshold, state = stopped > 10min)
- Canais: Webhook, Email, Slack, Telegram
- Regras via YAML:
  ```yaml
  alerts:
    - name: rpm_high
      condition: rpm > 5000
      duration: 30s
      severity: warning
      channels: [slack, email]
  ```
- Dedupe de alertas (evitar spam)
- Dashboard de alertas ativos

**Tech:**
- Celery + Redis para processamento async
- Templating com Jinja2

**Estimativa:** 2 semanas

---

### 🌟 Q1 2026 — Escalabilidade e Analytics (3-6 meses)

#### **F7: Multi-Máquina + Fleet Management**
**Objetivo:** Gerenciar múltiplos CNCs simultaneamente

**Entregas:**
- Adapter multi-threaded (1 thread por máquina)
- Dashboard com lista de máquinas
- Filtros: status, planta, tipo
- Agregações: Fleet OEE, uptime total
- API endpoint `/v1/fleet/summary`

**Frontend:**
```typescript
interface FleetSummary {
  total_machines: number;
  running: number;
  stopped: number;
  idle: number;
  avg_rpm: number;
  total_oee: number;
}
```

**Estimativa:** 3-4 semanas

---

#### **F8: Analytics + Relatórios**
**Objetivo:** Insights de negócio

**Dashboards:**
- **OEE Dashboard:** Disponibilidade, Performance, Qualidade
- **Trend Analysis:** RPM/Feed ao longo do tempo
- **Heatmaps:** Horários de maior produtividade
- **Comparative:** Machine A vs Machine B

**Métricas Calculadas:**
```python
OEE = Availability × Performance × Quality

Availability = (Operating Time) / (Planned Production Time)
Performance = (Actual Output) / (Theoretical Max Output)
Quality = (Good Parts) / (Total Parts Produced)
```

**Export:**
- PDF reports (WeasyPrint)
- CSV/Excel para análise externa
- Agendamento semanal/mensal

**Tech:**
- Recharts para gráficos
- Pandas para agregações
- FastAPI background tasks

**Estimativa:** 4 semanas

---

#### **F9: OPC-UA Support** 🔌
**Objetivo:** Suporte a protocolo industrial padrão IEC 62541

**Entregas:**
- Adapter OPC-UA (asyncua library)
- Auto-discovery de nodes
- Mapeamento automático de data items
- Coexistência com MTConnect

**Arquitetura:**
```
CNC (OPC-UA Server) → Adapter OPC-UA → Backend API → Dashboard
                    ↘ Adapter MTConnect ↗
```

**Estimativa:** 3 semanas

---

### 🚀 Q2 2026 — Inteligência e Edge (6-9 meses)

#### **F10: Machine Learning — Anomaly Detection**
**Objetivo:** Detectar padrões anormais automaticamente

**Modelos:**
1. **Isolation Forest:** Anomalias em RPM/Feed
2. **LSTM Autoencoder:** Sequências de estado incomuns
3. **Prophet:** Previsão de falhas

**Pipeline:**
```
Telemetry → Feature Engineering → Model Inference → Alert
```

**Features Extraídas:**
- Média móvel 5min, 30min
- Desvio padrão rolling
- Transições de estado por hora
- Tempo em cada estado

**Treinamento:**
- Dados históricos (30+ dias)
- Re-treino semanal automático
- A/B testing de modelos

**Tech:**
- scikit-learn, TensorFlow
- MLflow para tracking
- Feast para feature store

**Estimativa:** 6-8 semanas

---

#### **F11: Predictive Maintenance**
**Objetivo:** Prever falhas antes que ocorram

**Indicadores:**
- RUL (Remaining Useful Life)
- Probabilidade de falha em 7/14/30 dias
- Recomendações de manutenção

**Dashboard:**
- Risk score por máquina
- Histórico de predições vs. real
- ROI de manutenção preventiva

**Estimativa:** 8 semanas

---

#### **F12: Edge Computing**
**Objetivo:** Processamento local no chão de fábrica

**Arquitetura:**
```
┌─────────────┐         ┌──────────────┐         ┌────────┐
│ CNC Machine │────────▶│ Edge Gateway │────────▶│ Cloud  │
│ (MTConnect) │         │ (Raspberry Pi│         │ (API)  │
└─────────────┘         │  + Docker)   │         └────────┘
                        │              │
                        │ - Adapter    │
                        │ - Local DB   │
                        │ - Alertas    │
                        │ - ML Lite    │
                        └──────────────┘
```

**Benefícios:**
- ✅ Reduz latência (< 100ms)
- ✅ Funciona offline (eventual sync)
- ✅ Processa localmente (LGPD/GDPR)
- ✅ Reduz tráfego WAN

**Tech:**
- Docker Compose para edge stack
- SQLite para buffer local
- MQTT para sincronização
- Balena/Portainer para deploy remoto

**Estimativa:** 6 semanas

---

### 🏢 Q3-Q4 2026 — Enterprise e Integrações (9-18 meses)

#### **F13: Multi-Tenancy SaaS**
**Objetivo:** Modelo SaaS para múltiplos clientes

**Features:**
- Isolamento de dados por tenant (schema-per-tenant ou row-level security)
- Billing integrado (Stripe)
- Onboarding self-service
- Admin panel para gestão de clientes

**Auth:**
- OAuth2 + JWT
- SSO (SAML, OIDC)
- RBAC granular (admin, operator, viewer)

**Estimativa:** 8-10 semanas

---

#### **F14: Integrações ERP/MES**
**Objetivo:** Conectar com sistemas corporativos

**Sistemas Alvo:**
- SAP (iDoc, BAPI)
- Wonderware MES
- Plex Manufacturing Cloud
- Microsoft Dynamics 365

**Dados Exportados:**
- OEE para planejamento
- Downtime para análise de perdas
- Production counts para faturamento

**Tech:**
- Apache Kafka para event streaming
- API Gateway (Kong, Tyk)
- Webhook outbound

**Estimativa:** 6 semanas por integração

---

#### **F15: Mobile App (React Native)**
**Objetivo:** Monitoramento mobile para supervisores

**Features:**
- Push notifications de alertas
- Dashboard resumido
- Controle de máquinas (start/stop/pause)
- Offline-first com sync

**Plataformas:**
- iOS (App Store)
- Android (Play Store)

**Estimativa:** 10-12 semanas

---

#### **F16: Advanced Visualization**
**Objetivo:** Visualizações 3D e AR

**Features:**
- Gemini Digital 3D do CNC
- Heatmap 3D de temperatura/vibração
- AR overlays (iPad) para manutenção
- WebGL/Three.js para rendering

**Estimativa:** 8 semanas

---

### 🌐 Q1-Q2 2027 — Plataforma Completa (18-24 meses)

#### **F17: Marketplace de Plugins**
**Objetivo:** Extensibilidade via plugins de terceiros

**Arquitetura:**
- Plugin API (REST + Webhooks)
- Sandboxing (WASM, gVisor)
- Marketplace web (discovery, install, billing)

**Exemplos de Plugins:**
- Custom protocols (Siemens S7, Fanuc Focas)
- Integração específica de cliente
- Dashboards customizados

**Estimativa:** 12 semanas

---

#### **F18: Compliance e Certificações**
**Objetivo:** Conformidade regulatória

**Certificações Alvo:**
- ISO 27001 (Segurança da Informação)
- SOC 2 Type II (Auditoria de controles)
- CE Mark (Europa)
- UL Listed (Safety)

**Features:**
- Audit log completo
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Data retention policies
- GDPR/LGPD compliance

**Estimativa:** 16 semanas + auditoria externa

---

#### **F19: Global Scale**
**Objetivo:** Infraestrutura multi-região

**Arquitetura:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   US-East   │    │   EU-West   │    │   AP-South  │
│  (Primary)  │    │  (Replica)  │    │  (Replica)  │
└─────────────┘    └─────────────┘    └─────────────┘
       ↓                  ↓                   ↓
   Geo DNS Routing (Route53, Cloudflare)
```

**Tech:**
- Kubernetes multi-cluster
- CockroachDB (distributed SQL)
- CDN global (Cloudflare)
- Latency < 50ms P95 worldwide

**Estimativa:** 10 semanas

---

#### **F20: AI Copilot para Operadores**
**Objetivo:** Assistente IA conversacional

**Features:**
- Chat interface (LangChain + GPT-4)
- "Por que a máquina X parou?"
- "Qual o OEE da última semana?"
- "Me recomende manutenções prioritárias"
- Acesso via Slack, Teams, WhatsApp

**Tech:**
- LangChain para orchestration
- Vector DB (Pinecone) para RAG
- OpenAI API

**Estimativa:** 8 semanas

---

## 🛠️ Evoluções Técnicas Contínuas

### Arquitetura
- [ ] **Microservices:** Decompor monolito em serviços (Ingest, Query, Alerts, ML)
- [ ] **Event Sourcing:** CQRS para auditabilidade total
- [ ] **GraphQL:** Alternativa ao REST para queries complexas
- [ ] **gRPC:** Para comunicação interna de alta performance

### DevOps
- [ ] **CI/CD Avançado:** Blue-green deployment, canary releases
- [ ] **Chaos Engineering:** Testes de resiliência (Netflix Chaos Monkey)
- [ ] **Observability:** OpenTelemetry, Jaeger, Prometheus, Grafana
- [ ] **Auto-scaling:** HPA (Horizontal Pod Autoscaler) no K8s

### Segurança
- [ ] **Zero Trust:** Autenticação/autorização em cada request
- [ ] **Secrets Management:** Vault, AWS Secrets Manager
- [ ] **Penetration Testing:** Auditorias trimestrais
- [ ] **Dependency Scanning:** Snyk, Dependabot

### Performance
- [ ] **Caching avançado:** Redis Cluster, CDN
- [ ] **Read replicas:** PostgreSQL hot standby
- [ ] **Query optimization:** Índices, EXPLAIN ANALYZE
- [ ] **Load testing:** k6, Locust (100k+ req/s)

---

## 📊 Métricas de Sucesso (KPIs)

### Técnicas
- **Latência E2E:** P50 < 1s, P99 < 5s
- **Uptime:** 99.9% (SLA)
- **Perda de dados:** < 0.1%
- **TPS (Transactions/sec):** 1000+ sustentado

### Negócio
- **Máquinas monitoradas:** 10 → 100 → 1000
- **Clientes:** 1 → 10 → 50
- **ARR (Annual Recurring Revenue):** $0 → $100k → $1M
- **Net Promoter Score (NPS):** > 50

### Operacionais
- **MTTR (Mean Time to Repair):** < 30min
- **Deploy frequency:** Daily
- **Lead time for changes:** < 1 day
- **Change failure rate:** < 5%

---

## 💰 Modelo de Monetização

### Tiers
1. **Free Tier:** 1 máquina, 7 dias histórico, alertas básicos
2. **Professional:** $99/máquina/mês, 90 dias histórico, alertas avançados, ML
3. **Enterprise:** Custom pricing, histórico ilimitado, SLA 99.9%, suporte 24/7

### Add-ons
- **OPC-UA Support:** +$50/máquina/mês
- **Edge Gateway:** $299 hardware + $49/mês software
- **Custom Integrations:** $5k-20k one-time
- **Professional Services:** $200/hora

---

## 🚧 Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| **Escalabilidade técnica** | Alto | Médio | Arquitetura cloud-native, load testing contínuo |
| **Conformidade MTConnect** | Alto | Baixo | Testes automatizados, certificação oficial |
| **Competição (Fanuc, Mazak)** | Alto | Alto | Diferenciação via ML, UX superior, pricing agressivo |
| **Segurança (vazamento de dados)** | Crítico | Baixo | Pentests, bug bounty, encryption E2E |
| **Churn de clientes** | Médio | Médio | Customer success proativo, onboarding robusto |

---

## 👥 Time Necessário (Projeção)

### Atual (Q4 2025)
- 1 Full-stack Engineer (você)

### Q1 2026 (+3 meses)
- 1 Full-stack Engineer
- 1 Backend Engineer (Python/FastAPI)
- 1 Frontend Engineer (React/TypeScript)

### Q3 2026 (+9 meses)
- 2 Backend Engineers
- 1 Frontend Engineer
- 1 Data Engineer (ML/Analytics)
- 1 DevOps Engineer
- 1 Product Manager

### Q1 2027 (+18 meses)
- 4 Backend Engineers
- 2 Frontend Engineers
- 2 Data Engineers
- 2 DevOps Engineers
- 1 Security Engineer
- 1 Product Manager
- 1 UX Designer
- 2 Customer Success

---

## 📚 Stack Tecnológico Completo

### Backend
- **Core:** Python 3.11+, FastAPI, Pydantic
- **DB:** PostgreSQL 15+ (TimescaleDB), Redis 7+
- **Message Queue:** RabbitMQ, Kafka (para escala)
- **ORM:** SQLAlchemy 2.0, Alembic
- **Testing:** pytest, Hypothesis, Locust

### Frontend
- **Core:** React 18, TypeScript 5, Vite
- **UI:** TailwindCSS, shadcn/ui, Recharts
- **State:** Zustand, TanStack Query
- **Mobile:** React Native, Expo

### Data & ML
- **ML:** scikit-learn, TensorFlow, PyTorch
- **MLOps:** MLflow, Feast, Weights & Biases
- **Analytics:** Pandas, Polars, DuckDB

### Infra
- **Cloud:** AWS (ECS Fargate, RDS, S3, Lambda)
- **K8s:** EKS, Helm, ArgoCD
- **Observability:** OpenTelemetry, Jaeger, Grafana, Prometheus
- **CI/CD:** GitHub Actions, Terraform

### Protocolos
- **MTConnect:** HTTP/XML (atual)
- **OPC-UA:** asyncua
- **Modbus TCP:** pymodbus
- **MQTT:** Mosquitto, AWS IoT Core

---

## 🎯 Visão 2027

**"A plataforma líder em telemetria industrial multi-protocolo, com IA embarcada e edge computing, conectando 1000+ CNCs em 50+ plantas industriais globalmente."**

### Diferenciação
1. **✨ UX Superior:** Dashboard mais intuitivo que concorrentes
2. **🤖 ML Native:** Anomaly detection e predictive maintenance desde o core
3. **🔌 Multi-Protocolo:** MTConnect + OPC-UA + Modbus + Proprietários
4. **⚡ Edge-First:** Funciona offline, sincroniza quando online
5. **💰 Pricing Disruptivo:** 50% mais barato que Mazak iSMART, Fanuc Field System

---

## 📞 Próximas Ações Imediatas

### Esta Semana
- [x] Finalizar F3 (Dashboard PWA)
- [ ] Executar F4 Piloto de Campo (Novatech)
- [ ] Capturar métricas reais de produção

### Próximo Mês
- [ ] Iniciar F5 (Persistência + PostgreSQL)
- [ ] Design de F6 (Alertas + Notificações)
- [ ] Pitch para potenciais clientes beta

### Próximo Trimestre
- [ ] Fechar 3 clientes beta
- [ ] F7 Multi-Máquina em produção
- [ ] Roadshow em feiras industriais (FEIMEC, CIMATRON)

---

## 📄 Anexos

### Referências
- MTConnect Standard 2.3: https://www.mtconnect.org/
- OPC-UA Spec IEC 62541: https://opcfoundation.org/
- ISA-95 Enterprise-Control Integration: https://www.isa.org/
- Industry 4.0 Maturity Index: https://en.acatech.de/

### Competidores
- **Fanuc Field System:** $$$, closed ecosystem
- **Mazak iSMART Factory:** $$$, Mazak-only
- **IXON Cloud:** $$, VPN-focused
- **Tulip.co:** $$, low-code platform
- **MachineMetrics:** $$, analytics-focused

**Nosso Diferencial:** Open-source core + preço competitivo + ML native + multi-vendor

---

**Versão:** 1.0  
**Autor:** Vinicius John  
**Última Atualização:** 2025-11-05  
**Próxima Revisão:** 2026-01-01
