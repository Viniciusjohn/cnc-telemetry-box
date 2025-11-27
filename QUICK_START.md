# 🚀 CNC Telemetry Box - Quick Start Guide

## 📋 PRÉ-REQUISITOS

- Python 3.8+
- Node.js 16+
- PostgreSQL 13+ (opcional para produção)
- Redis 6+ (opcional para message queue)

---

## ⚡ START RÁPIDO

### **1. Backend**
```bash
# Instalar dependências
cd backend
pip install -r requirements.txt

# Iniciar servidor principal
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Health check
curl http://localhost:8001/box/healthz
```

### **2. Frontend**
```bash
# Instalar dependências
cd frontend
npm install

# Iniciar dev server
npm run dev

# Acessar: http://localhost:5173
```

### **3. Testes**
```bash
# Rodar todos os testes
python run_all_tests.py

# Teste específico
python test_multi_machine.py
```

---

## 🎯 FUNCIONALIDADES PRINCIPAIS

### **📊 Dashboard**
- Status em tempo real de múltiplas máquinas
- Indicadores OEE (Overall Equipment Effectiveness)
- Log de eventos com filtragem
- Interface responsiva

### **🏥 Health Monitoring**
- Diagnóstico completo do sistema
- Métricas de CPU, RAM, disco
- Status dos serviços
- Alertas e notificações

### **🔧 API Endpoints**
- `POST /v1/telemetry/ingest` - Ingestão de telemetria
- `GET /v1/machines` - Lista de máquinas
- `GET /v1/machines/{id}/status` - Status individual
- `GET /box/healthz` - Health check completo

---

## 🧪 EXEMPLOS DE USO

### **Enviar Telemetria**
```bash
curl -X POST http://localhost:8001/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "M80-001",
    "timestamp": "2025-01-01T10:00:00Z",
    "rpm": 3000,
    "feed_mm_min": 1000,
    "state": "running"
  }'
```

### **Consultar Status**
```bash
# Lista de máquinas
curl http://localhost:8001/v1/machines

# Status individual
curl http://localhost:8001/v1/machines/M80-001/status

# Grid view
curl http://localhost:8001/v1/machines/status?view=grid
```

### **Health Check**
```bash
curl http://localhost:8001/box/healthz | jq
```

---

## 🏗️ ARQUITETURA

### **Componentes Principais**
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React + TypeScript + TailwindCSS
- **Logging**: Structured logging com structlog
- **Rate Limiting**: Proteção contra abuse
- **Error Handling**: Robusto com HTTPExceptions

### **Melhorias Implementadas**
- ✅ Thread-safe status storage
- ✅ Circuit breaker pattern
- ✅ Event-driven architecture
- ✅ Dependency injection
- ✅ Message queue integration
- ✅ Microservices split

---

## 🔧 CONFIGURAÇÃO

### **Variáveis de Ambiente**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/cnc_telemetry

# Redis (opcional)
REDIS_URL=redis://localhost:6379/0

# API
API_BASE_URL=http://localhost:8001
LOG_LEVEL=INFO
```

### **Rate Limiting**
```python
# Configuração padrão
- 100 requests/minute por IP
- 10 requests/minute por máquina
- Retry-After header em excesso
```

---

## 📊 MONITORAMENTO

### **Logs Estruturados**
```json
{
  "timestamp": "2025-01-01T10:00:00Z",
  "level": "info",
  "logger": "telemetry_ingest",
  "machine_id": "M80-001",
  "event": "telemetry_received",
  "rpm": 3000,
  "state": "running"
}
```

### **Health Metrics**
- CPU, RAM, disco
- Uptime do sistema
- Status dos serviços
- Contador de requisições
- Taxa de erros

---

## 🚀 PRODUÇÃO

### **Docker Setup**
```bash
# Build
docker build -t cnc-telemetry-box .

# Run
docker run -p 8001:8001 cnc-telemetry-box
```

### **Microservices**
```bash
# Telemetry Service (port 8002)
python -m backend.app.microservices.telemetry_service

# Status Service (port 8003)
python -m backend.app.microservices.status_service
```

### **Backup Automático**
```bash
# Configurar cron
./scripts/backup/setup_cron.sh

# Backup manual
./scripts/backup/backup_pg.sh
```

---

## 🧪 DESENVOLVIMENTO

### **Estrutura de Diretórios**
```
cnc-telemetry-box/
├── backend/
│   ├── app/
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   ├── microservices/    # Microservices
│   │   └── *.py             # Core modules
│   ├── main.py              # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── contexts/         # React contexts
│   │   └── *.tsx            # App files
│   └── package.json
├── scripts/backup/           # Backup scripts
├── docs/                    # Documentation
└── tests/                   # Test files
```

### **Adicionar Nova Máquina**
```python
# Enviar primeira telemetria
POST /v1/telemetry/ingest
{
  "machine_id": "NOVA-MACHINE",
  "timestamp": "2025-01-01T10:00:00Z",
  "rpm": 0,
  "feed_mm_min": 0,
  "state": "idle"
}
```

### **Customizar Componentes**
```typescript
// Adicionar novo componente
export const NewComponent = () => {
  return <div>Novo componente</div>;
};
```

---

## 🐛 TROUBLESHOOTING

### **Problemas Comuns**

**Backend não inicia**
```bash
# Verificar dependências
pip install -r backend/requirements.txt

# Verificar database
python -c "from backend.app.db import engine; print(engine.url)"
```

**Frontend não carrega**
```bash
# Verificar Node.js
node --version
npm --version

# Reinstalar dependências
rm -rf node_modules package-lock.json
npm install
```

**Rate Limiting**
```bash
# Verificar headers
curl -I http://localhost:8001/v1/telemetry/ingest

# Aguardar Retry-After
sleep $(curl -s -w '%{http_code}' http://localhost:8001/v1/telemetry/ingest | grep -o '[0-9]*')
```

### **Logs de Debug**
```bash
# Backend logs
export LOG_LEVEL=DEBUG
python -m backend.main

# Frontend logs
# Abrir DevTools > Console
```

---

## 📚 RECURSOS

### **Documentação**
- `README_ROADMAP.md` - Roadmap completo
- `docs/REDE_SEGURA_PILOTO.md` - Configuração de rede
- `docs/API_REFERENCE.md` - Referência da API

### **Testes**
- `test_multi_machine.py` - Teste multi-máquina
- `test_frontend_integration.py` - Integração frontend
- `test_microservices.py` - Microservices
- `run_all_tests.py` - Executar todos

### **Scripts**
- `scripts/backup/` - Backup e restore
- `run_all_tests.py` - Test runner
- `QUICK_START.md` - Este guia

---

## 🎞️ SUPORTE

### **Health Check**
```bash
curl http://localhost:8001/box/healthz
```

### **Logs**
```bash
# Verificar logs estruturados
tail -f logs/app.log | jq
```

### **Performance**
```bash
# Verificar métricas
curl http://localhost:8001/box/healthz | jq '.performance'
```

---

**🚀 CNC Telemetry Box v2.0 - Enterprise Grade**  
**Pronto para escala industrial!** 🎊
