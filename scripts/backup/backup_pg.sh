#!/bin/bash
# CNC Telemetry Box - Backup Automático do PostgreSQL
# Uso: ./backup_pg.sh
# Cria backup diário e limpa backups antigos

set -e  # Aborta em qualquer erro

# Configuração
DB_NAME="cnc_telemetry"
DB_USER="cncbox"
CONTAINER_NAME="cnc-telemetry-box-db-1"  # Ajustar se necessário
BACKUP_DIR="/opt/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${DB_NAME}-${TIMESTAMP}.sql"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função de log
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Verificar se o container está rodando
if ! docker ps | grep -q $CONTAINER_NAME; then
    error "Container $CONTAINER_NAME não está rodando"
    exit 1
fi

# Criar diretório de backup
mkdir -p $BACKUP_DIR
log "Diretório de backup: $BACKUP_DIR"

# Verificar espaço em disco antes do backup
AVAILABLE_SPACE=$(df $BACKUP_DIR | tail -1 | awk '{print $4}')
if [ $AVAILABLE_SPACE -lt 1048576 ]; then  # < 1GB em KB
    warning "Espaço em disco baixo: $(($AVAILABLE_SPACE / 1024))MB disponível"
fi

# Executar backup
log "Iniciando backup do PostgreSQL..."
log "Database: $DB_NAME"
log "Container: $CONTAINER_NAME"

if docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME > "${BACKUP_DIR}/${BACKUP_FILE}"; then
    log "Backup criado: ${BACKUP_DIR}/${BACKUP_FILE}"
else
    error "Falha ao criar backup"
    exit 1
fi

# Verificar se o arquivo foi criado e não está vazio
if [ ! -s "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    error "Arquivo de backup está vazio ou não foi criado"
    exit 1
fi

# Comprimir backup
log "Comprimindo backup..."
gzip "${BACKUP_DIR}/${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Verificar tamanho do backup
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log "Tamanho do backup: $BACKUP_SIZE"

# Limpar backups antigos
log "Limpando backups antigos (>$RETENTION_DAYS dias)..."
DELETED_COUNT=$(find $BACKUP_DIR -name "${DB_NAME}-*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ $DELETED_COUNT -gt 0 ]; then
    log "Removidos $DELETED_COUNT backups antigos"
else
    log "Nenhum backup antigo para remover"
fi

# Listar backups atuais
log "Backups disponíveis:"
ls -lh $BACKUP_DIR/${DB_NAME}-*.sql.gz 2>/dev/null || warning "Nenhum backup encontrado"

# Verificar espaço em disco após backup
DISK_USAGE=$(df $BACKUP_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    warning "Disco com ${DISK_USAGE}% de uso"
elif [ $DISK_USAGE -gt 90 ]; then
    error "Disco com ${DISK_USAGE}% de uso - ação necessária!"
fi

# Estatísticas finais
TOTAL_BACKUPS=$(ls $BACKUP_DIR/${DB_NAME}-*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh $BACKUP_DIR/${DB_NAME}-*.sql.gz 2>/dev/null | cut -f1 || echo "0B")

log "Backup concluído com sucesso!"
log "Total de backups: $TOTAL_BACKUPS"
log "Espaço total ocupado: $TOTAL_SIZE"
log "Próximo backup em: $(date -d '+1 day' '+%Y-%m-%d %H:%M:%S')"
