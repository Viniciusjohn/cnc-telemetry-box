# Piloto CNC Telemetry Box - Nestor

## 📦 Versão Baseline: `box-pilot-baseline`

**Data**: 2025-11-27  
**Tag**: `box-pilot-baseline`  
**Commit**: `6e31571`

---

## 🖥️ **Requisitos de Hardware**

### **Mínimo recomendado**
- **CPU**: 2 cores (Intel Celeron J4125+ ou similar)
- **RAM**: 4GB DDR4
- **Armazenamento**: 64GB SSD
- **Rede**: Ethernet 10/100 Mbps
- **Portas**: 1x USB (para setup inicial), 1x HDMI (opcional)

### **Ideal para produção**
- **CPU**: 4 cores (Intel i3/N100 ou similar)
- **RAM**: 8GB DDR4
- **Armazenamento**: 128GB SSD
- **Rede**: Ethernet Gigabit
- **Alimentação**: 12V contínua (UPS recomendado)

### **Rede**
- **IP fixo ou reserva DHCP** para acesso estável
- **Porta 8001** liberada para API
- **Porta 80/443** para dashboard
- **Acesso internet** para Docker download

---

## 🔌 **Configurando Máquinas CNC**

### **O que o Nestor precisa fornecer**
Para cada máquina CNC:
1. **ID estável** (ex.: M80-001, M80-002, TORUS-01)
2. **IP e porta** do agente MTConnect/gateway
3. **Formato de dados** (JSON/XML, endpoints)

### **Como registrar no Box**
```bash
# Editar configuração das máquinas
# Arquivo: .env ou config/machines.yaml
TELEMETRY_MACHINES="M80-001:192.168.1.100:7878,M80-002:192.168.1.101:7878"

# Nota: API POST /machines será implementada em v2
# Por enquanto, configure via .env e restart do container
```

### **Validando conexão**
```bash
# Verificar se máquina aparece no healthz
curl http://IP_DO_BOX:8001/box/healthz | jq '.machine_count_by_state'

# Verificar status da máquina (endpoint real)
curl http://IP_DO_BOX:8001/status/M80-001/status

# Verificar eventos da máquina (endpoint real)
curl http://IP_DO_BOX:8001/status/M80-001/events
```

### **Endpoints API disponíveis (baseline)**
- `GET /box/healthz` - Health check completo
- `GET /status/{machine_id}/status` - Status atual da máquina
- `GET /status/{machine_id}/events` - Eventos recentes da máquina
- `GET /oee/{machine_id}` - Métricas OEE (se disponível)
- `GET /history/{machine_id}` - Histórico de telemetria

---

## 🎯 **O que esta versão entrega para o Nestor**

### **Visibilidade em tempo real das máquinas**
- **Estados das máquinas**: running, idle, offline (baseado em heartbeat)
- **Contagem total**: quantas máquinas estão conectadas ao sistema
- **Health check completo**: status do banco, sistema, e serviços

### **Endpoint `/box/healthz`**
```json
{
  "status": "healthy",
  "box_version": "1.0",
  "machine_count": {
    "total_machines": 5,
    "telemetry_machines": 5,
    "status_machines": 0
  },
  "machine_count_by_state": {
    "running": 0,
    "idle": 0,
    "offline": 4
  },
  "db_status": {
    "status": "connected",
    "dialect": "postgresql",
    "table_count": 3
  },
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "uptime_formatted": "2h 15m"
  }
}
```

---

## 🛠️ **Instalação em Campo (5 passos)**

### **1. Preparar o hardware**
- Mini-PC com Ubuntu Server 22.04+
- Conexão de rede estável
- Acesso à internet (para Docker)

### **2. Instalar Docker**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Reboot e login novamente
```

### **3. Clonar e configurar**
```bash
git clone https://github.com/Viniciusjohn/cnc-telemetry-box.git
cd cnc-telemetry-box
cp .env.example .env
# Editar .env se necessário (DATABASE_URL, etc.)
```

### **4. Subir os serviços**
```bash
docker compose up -d --build
docker compose ps  # Verificar: db, backend, adapter, sync, frontend
```

### **5. Validar instalação**
```bash
# Health check local
curl http://localhost:8001/box/healthz

# Acessar dashboard
# Abrir navegador: http://IP_DO_BOX/
```

---

## ✅ **Checklist de Validação**

- [ ] Docker containers todos "running"
- [ ] `/box/healthz` retorna `status: "healthy"`
- [ ] `box_version: "1.0"` presente
- [ ] `machine_count_by_state` mostra contagem
- [ ] Dashboard abre em navegador
- [ ] systemd service habilitado (opcional)

---

## 🎯 **Valor Demonstrável**

### **Para o Nestor (PCP/Manutenção)**
1. **Veja quais máquinas estão trabalhando agora** - sem precisar ir ao chão de fábrica
2. **Identifique problemas rapidamente** - máquinas offline aparecem imediatamente
3. **Monitore saúde do sistema** - banco, CPU, memória em um só lugar
4. **Interface web simples** - acessível de qualquer PC na rede

### **Para você (implantação)**
1. **Instalação em 15 minutos** - scripts prontos, configuração mínima
2. **Rollback seguro** - `git checkout box-pilot-baseline` volta para estável
3. **Evolução controlada** - cada mudança via workflow Windows→Box
4. **Monitoramento remoto** - healthz acessível via curl/navegador

---

## 🚨 **Suporte em Campo**

### **Problemas comuns**
- **Containers não sobem**: verificar Docker daemon (`sudo systemctl status docker`)
- **Healthz retorna erro**: verificar logs (`docker compose logs backend`)
- **Não acessa via rede**: verificar firewall (`sudo ufw status`)

### **Comandos úteis**
```bash
# Ver logs
docker compose logs -f backend

# Reiniciar serviços
docker compose restart

# Parar tudo
docker compose down

# Voltar para baseline
git checkout box-pilot-baseline
docker compose up -d --build
```

---

## 🔄 **Próximos Passos**

1. **Primeira melhoria focada**: Card visual no dashboard mostrando estados das máquinas
2. **Coleta de feedback**: O que Nestor mais usa? healthz ou dashboard?
3. **Evolução incremental**: aplicar workflow Windows→Box para cada ajuste

---

## 📞 **Contato**

- **Documentação completa**: `README.md`, `DEPLOYMENT.md`
- **Histórico de mudanças**: `MIGRATION_LOG.md`
- **Issues/Sugestões**: GitHub repository

---

**Baseline pronto para demonstração de valor imediato!** 🎯
