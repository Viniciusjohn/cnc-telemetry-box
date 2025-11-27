#!/bin/bash
# CNC Telemetry Box - Setup Cron para Backup Automático
# Configura job diário de backup às 02:00 AM

set -e

# Configuração
SCRIPT_PATH="/opt/cnc-telemetry-box/scripts/backup/backup_pg.sh"
LOG_FILE="/var/log/telemetry-backup.log"
CRON_ENTRY="0 2 * * * $SCRIPT_PATH >> $LOG_FILE 2>&1"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    error "Este script precisa ser executado como root (sudo)"
    echo "Uso: sudo $0"
    exit 1
fi

# Verificar se o script de backup existe
if [ ! -f "$SCRIPT_PATH" ]; then
    error "Script de backup não encontrado: $SCRIPT_PATH"
    exit 1
fi

# Tornar script executável
chmod +x "$SCRIPT_PATH"
log "Script de backup marcado como executável"

# Verificar cron atual
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# Verificar se já existe o entry
if echo "$CURRENT_CRON" | grep -F "$SCRIPT_PATH" >/dev/null; then
    warning "Job de backup já existe no crontab"
    echo "Job atual:"
    echo "$CURRENT_CRON" | grep -F "$SCRIPT_PATH"
    echo
    read -p "Deseja remover e recriar? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Remover entry existente
        NEW_CRON=$(echo "$CURRENT_CRON" | grep -v -F "$SCRIPT_PATH")
        echo "$NEW_CRON" | crontab -
        log "Job antigo removido"
    else
        log "Mantendo configuração atual"
        exit 0
    fi
fi

# Adicionar novo entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

log "Job de backup adicionado ao crontab"
info "Horário: 02:00 AM todos os dias"
info "Script: $SCRIPT_PATH"
info "Log: $LOG_FILE"

# Criar arquivo de log se não existir
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"
log "Arquivo de log criado: $LOG_FILE"

# Mostrar cron atual
echo
log "Crontab atual:"
crontab -l | grep -v "^#"

# Testar execução (opcional)
echo
read -p "Deseja testar o backup agora? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    log "Executando backup de teste..."
    if $SCRIPT_PATH; then
        log "Backup de teste concluído com sucesso!"
    else
        error "Backup de teste falhou"
        exit 1
    fi
fi

echo
log "✅ Setup do cron concluído!"
info "Próximo backup automático: $(date -d '02:00 tomorrow' '+%Y-%m-%d %H:%M:%S')"
info "Para ver logs: tail -f $LOG_FILE"
info "Para remover: crontab -e (remova a linha do backup)"
