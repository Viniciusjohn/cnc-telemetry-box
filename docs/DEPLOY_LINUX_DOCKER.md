# Deploy Linux - CNC Telemetry Box (Docker + Postgres)

Este documento descreve como rodar o **CNC Telemetry Box** em um servidor Linux
usando **Docker** e **Docker Compose**.

> Importante: nao execute estes comandos como root diretamente; use um usuario
> com permissao de docker (ex.: grupo `docker`) ou `sudo` quando necessario.

## Roteiro rapido para VM (6 comandos)

Na VM Linux (ex.: Ubuntu Server), logado como usuario normal (ex.: `vinicius`):


```bash
cp .env.example .env
# editar a senha de banco em .env (POSTGRES_PASSWORD)
```

O Docker Compose vai ler automaticamente o arquivo `.env` na raiz do repo e
usar as variaveis:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `DATABASE_URL`
- `API_HOST` / `API_PORT`

### 2. Baixar imagens base

```bash
docker compose pull
```

### 3. Subir apenas o banco de dados

```bash
docker compose up -d db
```

- Cria um container `db` com imagem `postgres:16-alpine`.
- Persiste os dados em `./data/postgres` no host.

### 4. Subir o backend

> Observacao: o servico `backend` usa `build: ./backend`, entao e preciso ter
> um `Dockerfile` no diretorio `backend/` (criado na Missao 4).

```bash
docker compose up -d backend
```

Isso vai:

- Construir a imagem do backend a partir de `backend/`.
- Criar um container `backend` conectado ao mesmo network do `db`.
- Configurar a variavel `DATABASE_URL` apontando para o servico `db`.
- Expor a API em `http://localhost:8001` no host.

### 5. Verificar se os containers estao rodando

```bash
docker compose ps
```

### 6. Checar logs do backend (opcional)

```bash
docker logs backend --tail=50
```

### 7. Testar o endpoint de healthcheck

```bash
curl http://localhost:8001/healthz
```

Esperado: resposta HTTP 200 com um JSON similar a:

```json
{
  "status": "ok",
  "service": "cnc-telemetry",
  "version": "v0.3",
  "worker_m80_enabled": true,
  "worker_consecutive_errors": 0
}
```

## Subir stack completo (dev)

Para subir todos os servicos (db, backend, adapter, sync e frontend) em modo
de desenvolvimento:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8001/healthz
```

Comandos uteis para inspecionar os containers:

```bash
docker logs backend --tail=50
docker logs adapter --tail=20
docker logs sync --tail=20
```

Se tudo estiver ok:

- `backend` responde em `http://localhost:8001/healthz`.
- `adapter` mostra eventos sendo enviados para `/v1/telemetry/ingest`.
- `sync` imprime heartbeats periodicos (stub).

## Acessar UI do Box

Com o servico `frontend` ativo, a UI fica exposta na porta 80 do host.

De outro PC na mesma rede:

- Acessar `http://<IP_DO_BOX>/` no navegador.
- Conferir no DevTools (aba Network) se as requisicoes para a API retornam
  HTTP 200.

## Habilitar sistema como servico (systemd)

No Box real (mini-PC Linux), a ideia e que o projeto seja instalado em
`/opt/cnc-telemetry-box` e controlado via `systemd`.

Passos sugeridos (nao executar como root direto, usar `sudo` quando
necessario):

```bash
# copiar projeto para /opt
sudo mkdir -p /opt/cnc-telemetry-box
sudo cp -r /caminho/do/repo/* /opt/cnc-telemetry-box

# copiar o service
sudo cp /opt/cnc-telemetry-box/deploy/linux/cnc-telemetry-box.service /etc/systemd/system/

# recarregar systemd
sudo systemctl daemon-reload

# habilitar e iniciar
sudo systemctl enable cnc-telemetry-box
sudo systemctl start cnc-telemetry-box

# checar status
sudo systemctl status cnc-telemetry-box
```

Depois disso, um reboot do Box deve subir automaticamente todo o stack do
CNC Telemetry Box. Sem logar no mini-PC, basta acessar a UI a partir de outro
computador usando `http://<IP_DO_BOX>/`.
