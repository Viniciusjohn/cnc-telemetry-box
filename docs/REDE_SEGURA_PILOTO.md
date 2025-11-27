# Configuração de Rede Segura - CNC Telemetry Box Piloto

## 🎯 Objetivo

Isolar o CNC Telemetry Box na rede interna da fábrica, garantindo acesso controlado e segurança mínima para o piloto.

---

## 📋 Pré-requisitos

### Hardware de Rede
- **Switch gerenciável** (preferencial) ou switch simples
- **VLAN capability** (opcional, mas recomendado)
- **IP fixo disponível** na rede interna
- **Cabo Ethernet** para conexão do Box

### Conhecimento Necessário
- Acesso ao administrador de rede da fábrica
- Permissão para configurar firewall/regras
- Noções básicas de IP e sub-redes

---

## 🔧 Configuração Recomendada

### Opção 1: Isolamento por VLAN (Ideal)

```
VLAN 10: Rede Corporativa
├── Servidores, estações, internet
└── Acesso geral

VLAN 20: Rede Industrial (CNC Telemetry Box)
├── CNC Telemetry Box: 192.168.20.10
├── Máquinas CNC: 192.168.20.50-100
├── MTConnect Agents: 192.168.20.50-100:5000
└── PCs da Produção: 192.168.20.200-250
```

**Configuração Switch:**
```bash
# Porta do Box
interface GigabitEthernet1/0/10
  switchport access vlan 20
  switchport mode access
  spanning-tree portfast

# Portas das CNCs
interface range GigabitEthernet1/0/11-20
  switchport access vlan 20
  switchport mode access
```

### Opção 2: Sub-rede Dedica

```
Rede Principal: 192.168.1.0/24
├── Servidores, internet, etc.

Sub-rede Industrial: 192.168.50.0/24
├── Gateway: 192.168.50.1
├── CNC Telemetry Box: 192.168.50.10
├── Máquinas CNC: 192.168.50.50-100
└── PCs Produção: 192.168.50.200-250
```

**Regras Firewall:**
```bash
# Permitir acesso interno (produção)
iptables -A INPUT -s 192.168.50.0/24 -p tcp --dport 80 -j ACCEPT

# Bloquear acesso externo
iptables -A INPUT -p tcp --dport 80 -j DROP

# Permitir management (TI apenas)
iptables -A INPUT -s 192.168.1.100 -p tcp --dport 22 -j ACCEPT  # SSH
iptables -A INPUT -s 192.168.1.100 -p tcp --dport 443 -j ACCEPT # HTTPS futuro
```

---

## 🚀 Passo a Passo - Instalação

### 1. Configuração IP Fixo no Box

```bash
# Editar configuração de rede
sudo nano /etc/netplan/01-netcfg.yaml

network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.50.10/24]
      gateway4: 192.168.50.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]

# Aplicar configuração
sudo netplan apply
```

### 2. Validar Conectividade

```bash
# Testar gateway
ping 192.168.50.1

# Testar DNS
ping 8.8.8.8

# Testar resolução
nslookup google.com

# Verificar IP
ip addr show eth0
```

### 3. Configurar Firewall do Box

```bash
# Regras básicas
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (management)
sudo ufw allow from 192.168.1.100 to any port 22

# Permitir HTTP apenas da rede interna
sudo ufw allow from 192.168.50.0/24 to any port 80

# Ativar firewall
sudo ufw enable

# Verificar status
sudo ufw status verbose
```

### 4. Validar Acesso

```bash
# De dentro da rede industrial (PC produção)
curl http://192.168.50.10/healthz

# De fora da rede industrial (deve falhar)
curl http://192.168.50.10/healthz
# Expected: timeout ou connection refused
```

---

## 🔍 Validação de Segurança

### Teste de Portas Abertas

```bash
# Scan da rede interna (deve mostrar apenas porta 80)
nmap -sS -p 1-1000 192.168.50.10

# Expected:
# PORT   STATE SERVICE
# 22/tcp filtered ssh
# 80/tcp open  http
# 443/tcp closed https
# 5432/tcp filtered postgres
```

### Teste de Acesso Externo

```bash
# De uma rede externa (via VPN ou internet)
telnet 192.168.50.10 80
# Expected: Connection timed out

# Teste específico do dashboard
curl -I http://192.168.50.10/
# Expected: 200 OK apenas da rede interna
```

---

## 📱 Acesso para Usuários

### PCs da Produção
- **URL**: http://192.168.50.10
- **Requisitos**: Navegador moderno, mesma rede
- **Funcionalidade**: Dashboard completo

### PCs da TI/Administração
- **SSH**: ssh admin@192.168.50.10 (se permitido)
- **HTTPS**: https://192.168.50.10 (futuro)
- **Management**: Configuração e diagnósticos

### Acesso Remoto (Opcional)
```bash
# Via VPN corporativa
ssh admin@192.168.50.10

# Via jump server
ssh -J jump@corporate.com admin@192.168.50.10
```

---

## 🚨 Recomendações de Segurança

### Básico (Piloto)
- ✅ IP fixo configurado
- ✅ Apenas porta 80 exposta
- ✅ Acesso limitado à rede interna
- ✅ Firewall básico ativo

### Intermediário (Produção)
- 🔄 HTTPS com certificado
- 🔄 Autenticação simples (user/senha)
- 🔄 Logs de acesso
- 🔄 Backup automático configurado

### Avançado (Scale)
- ⏳ VLAN dedicada
- ⏳ IDS/IPS na rede
- ⏳ Monitoramento SIEM
- ⏳ Hardening completo

---

## 🆘 Troubleshooting

### "Não consigo acessar o dashboard"
```bash
# 1. Verificar se Box está online
ping 192.168.50.10

# 2. Verificar se serviço está rodando
docker ps | grep cnc-telemetry

# 3. Verificar logs
docker logs cnc-telemetry-box-backend-1

# 4. Verificar firewall
sudo ufw status
```

### "Dashboard acessível de fora da rede"
```bash
# Verificar regras firewall
sudo iptables -L -n

# Verificar configuração switch
show vlan brief
show interface status
```

### "Conexão com CNC falha"
```bash
# Testar conectividade com CNC
telnet 192.168.50.50 5000

# Verificar MTConnect
curl http://192.168.50.50:5000/probe
```

---

## 📞 Contato de Suporte

- **Rede**: Administrador de TI da fábrica
- **Aplicação**: Suporte CNC Telemetry
- **Emergência**: 24/7 via telefone/email

---

**Revisão**: Válido para piloto v1 - Atualizar para produção conforme necessidade
