# Email para Novatech — Agendamento Piloto F4

**Para:** nestor@novatech.com.br (ou contato técnico)  
**CC:** [Seu gerente/time]  
**Assunto:** Agendamento de Piloto - Sistema de Telemetria CNC (Mitsubishi)

---

Olá Nestor,

Finalizamos a validação do sistema de telemetria CNC em laboratório e estamos prontos para o piloto de campo na Novatech.

## 📊 Resultados de Laboratório (F2 + F3)

✅ **Soak test 30 min:** 898 amostras, 0.22% perda, 0 erros  
✅ **Dashboard PWA:** Polling 2s, 4 cards (RPM, Feed, Estado, Timestamp)  
✅ **MTConnect validado:** RotaryVelocity, PathFeedrate (mm/s→mm/min), Execution normalizado  
✅ **Headers canônicos:** Cache-Control: no-store, CORS, fingerprint

**Repositório:** https://github.com/Viniciusjohn/cnc-telemetry

---

## 📋 Informações Necessárias para o Piloto

Para executar o teste no campo, precisamos confirmar:

### 1. Máquina CNC
- **Série:** M70 / M700 / M80 / M800 / Outra?
- **Serial/Identificação:** _______________
- **Localização física:** _______________

### 2. Conectividade (MTConnect Agent)

**Opção A - Agent já instalado:**
- IP da máquina: `192.168.1.___`
- Porta do MTConnect Agent: `____` (geralmente 5000)
- Versão do Agent: _______________

**Opção B - Agent não disponível:**
- Podemos instalar o **MTConnect Data Collector** (Edgecross/Mitsubishi)?
- Alternativa: SDK nativo da Mitsubishi (requer ajustes no adapter)

### 3. Janela de Testes
- **Data sugerida:** ___/___/2025
- **Horário:** ___:___ às ___:___
- **Duração mínima:** 2 horas (idealmente sem interromper produção)
- **Pessoa de contato no local:** _______________

---

## 🎯 Objetivo do Piloto

### Validações Técnicas
- Coleta contínua de dados por **30 minutos** sem interrupções
- Confirmação de precisão de **RPM e Feed** (±1% vs painel físico)
- Demonstração do **dashboard mobile/desktop** atualizando em tempo real

### Entregas
- Relatório técnico com métricas (perda, latência, transições de estado)
- Screenshots do dashboard (desktop + mobile)
- Confirmação de aceite técnico

---

## 🔧 Requisitos Técnicos

### Rede
- Acesso à rede da máquina (Wi-Fi ou cabeado)
- Porta 5000-5010 liberada no firewall (se houver)
- Opcional: Laptop conectado na mesma VLAN da máquina

### Software
- MTConnect Agent rodando na máquina ou edge
- Navegador moderno (Chrome/Edge/Safari) para visualizar dashboard
- Acesso SSH/VNC ao edge (se necessário)

---

## 📅 Próximos Passos

1. **Confirmar informações** acima (série, IP, janela)
2. **Agendar data/horário** com disponibilidade da equipe técnica
3. **Preparar ambiente** (Agent rodando, rede configurada)
4. **Executar piloto** (30 min soak + validações)
5. **Aceite técnico** e próximos passos

---

## 📞 Contato

Em caso de dúvidas ou para agendar reunião de alinhamento:

- **Email:** [seu.email@empresa.com]
- **Telefone/WhatsApp:** [+55 XX XXXXX-XXXX]
- **Disponibilidade:** Segunda a sexta, 8h-18h

---

Aguardamos retorno para prosseguirmos com o agendamento.

Atenciosamente,

**[Seu Nome]**  
[Seu Cargo]  
[Sua Empresa]

---

## 📎 Anexos

- Relatório F2 (Soak Test): https://github.com/Viniciusjohn/cnc-telemetry/issues/3
- Planejamento F4 (Campo): `docs/F4_PLANEJAMENTO.md`
- Guia de Campo: `docs/CAMPO_GUIA_EXECUTIVO.md`
