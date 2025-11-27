# CNC-Genius Telemetria

Serviço de telemetria CNC do projeto CNC-Genius (MTConnect → JSON canônico → dashboard).

## 🎯 Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React + TypeScript + Vite
- **PWA:** Service Worker + Manifest
- **Testes:** Playwright
- **Protocolo:** MTConnect (padrão aberto)

---

## Sobre este repositório — CNC Telemetry Box (Linux + Docker + Postgres)

Este repositório contém o **CNC Telemetry Box v1** - gateway local de telemetria CNC para Ubuntu Server + Docker + systemd.

**Escopo oficial**: Edge appliance Linux headless para coleta de telemetria CNC em fábrica:
- Execução em mini-PC industrial rodando Ubuntu Server
- Stack completo em containers Docker (db, backend, adapter, sync, frontend)
- Banco PostgreSQL para armazenamento local de histórico
- Dashboard web acessível via HTTP na rede interna
- Deploy padrão via Docker Compose + systemd

**Documentação principal**:
- `docs/CNC_TELEMETRY_BOX_V1.md` - Visão geral do produto Box v1
- `docs/DEPLOY_LINUX_DOCKER.md` - Deploy oficial (6 comandos)
- `deploy/linux/cnc-telemetry-box.service` - Serviço systemd

**Legado Windows**: Componentes do piloto antigo foram isolados em `legacy_windows/` e não fazem parte do fluxo oficial do Box.

---

## Como clonar e subir o CNC Telemetry Box (Linux + Docker + Postgres)

Mini-servidor de telemetria CNC para rodar como **appliance Linux headless**,
usando **Docker + Docker Compose + PostgreSQL**.

Documentação funcional do produto:
- `docs/CNC_TELEMETRY_BOX_V1.md`

### 1. Clonar o repositório

```bash
git clone https://github.com/Viniciusjohn/cnc-telemetry-box.git
cd cnc-telemetry-box
```

### 2. Configurar ambiente

```bash
cp .env.example .env
# Editar POSTGRES_PASSWORD em .env
```

### 3. Subir o stack completo (deploy oficial)

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8001/healthz
```

**Validação**:
- ✅ Backend responde em `http://localhost:8001/healthz`
- ✅ Frontend disponível em `http://localhost:80`
- ✅ Adapter demo envia eventos para `/v1/telemetry/ingest`

### 4. Acessar UI do Box

```bash
# Localmente
curl http://localhost:80

# Via browser
http://localhost
```

---

## 🗂️ Estrutura do Repositório

```
cnc-telemetry-box/
├── docker-compose.yml          # Stack oficial do Box
├── backend/                     # FastAPI + routers + multi-máquina
├── frontend/                    # React dashboard
├── adapter/                     # MTConnect adapter
├── docs/                        # Documentação Linux
│   ├── DEPLOY_LINUX_DOCKER.md   # Deploy oficial
│   └── CNC_TELEMETRY_BOX_V1.md  # Visão do produto
├── deploy/linux/                # systemd + configs
└── legacy_windows/              # ⚠️ Piloto antigo (histórico)
```

---

## 📋 Deploy em Produção

### Ubuntu Server + systemd

1. **Setup do Box**:
   ```bash
   sudo apt update && sudo apt install docker.io docker-compose
   git clone https://github.com/Viniciusjohn/cnc-telemetry-box.git
   cd cnc-telemetry-box
   cp .env.example .env
   # Editar POSTGRES_PASSWORD em .env
   ```

2. **Instalar serviço systemd**:
   ```bash
   sudo cp deploy/linux/cnc-telemetry-box.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable cnc-telemetry-box
   sudo systemctl start cnc-telemetry-box
   ```

3. **Validar**:
   ```bash
   sudo systemctl status cnc-telemetry-box
   curl http://localhost:8001/healthz
   ```

---

## ⚠️ Legado Windows

Componentes do piloto Windows foram movidos para `legacy_windows/`:
- Scripts `.bat`/`.ps1` de instalação
- PyInstaller builds para `.exe`
- NSSM service installs

**Estes arquivos não fazem parte do fluxo oficial do CNC Telemetry Box v1.**

---

## 🔧 Desenvolvimento

- **Linux**: Ambiente nativo + Docker
- **Windows**: Docker Desktop (containers Linux)
- **Client**: Browser (http://box-ip:80)

### Backend local (dev)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

### Frontend local (dev)

```bash
cd frontend
npm install
npm run dev
# Acessar: http://localhost:5173
```

---

## 📊 Funcionalidades Implementadas

- ✅ **Multi-máquina**: Seleção e monitoramento de múltiplas CNCs
- ✅ **MTConnect**: Adapter compatível com padrão MTConnect v1.7
- ✅ **Dashboard React**: UI responsiva com updates em tempo real
- ✅ **API REST**: Endpoints canônicos para integração
- ✅ **Persistência**: PostgreSQL com histórico completo
- ✅ **Sync opcional**: Envio de dados para nuvem quando disponível

---

## 📚 Documentação Adicional

- `docs/CNC_TELEMETRY_BOX_V1.md` - Especificações do produto
- `docs/DEPLOY_LINUX_DOCKER.md` - Guia detalhado de deploy
- `docs/MTCONNECT_COMPLIANCE.md` - Compatibilidade MTConnect
- `deploy/linux/cnc-telemetry-box.service` - Configuração systemd

---

**CNC Telemetry Box v1 - Gateway local de telemetria CNC**  
*Ubuntu Server + Docker + PostgreSQL + systemd*
