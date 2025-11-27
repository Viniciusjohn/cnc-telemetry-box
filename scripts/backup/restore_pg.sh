#!/bin/bash
# CNC Telemetry Box - Restore do PostgreSQL
# Uso: ./restore_pg.sh <backup-file.sql.gz>
# Restaura backup completo do banco de dados

set -e  # Aborta em qualquer erro

# Configuração
DB_NAME="cnc_telemetry"
DB_USER="cncbox"
CONTAINER_NAME="cnc-telemetry-box-db-1"  # Ajustar se necessário

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Verificar argumentos
if [ $# -ne 1 ]; then
    error "Uso: $0 <backup-file.sql.gz>"
    echo
    echo "Exemplos:"
    echo "  $0 /opt/backups/cnc_telemetry-20251127-0200.sql.gz"
    echo "  $0 cnc_telemetry-20251127-0200.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Verificar se o arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    error "Arquivo de backup não encontrado: $BACKUP_FILE"
    exit 1
fi

# Verificar se o container está rodando
if ! docker ps | grep -q $CONTAINER_NAME; then
    error "Container $CONTAINER_NAME não está rodando"
    exit 1
fi

# Informações do backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_DATE=$(stat -c %y "$BACKUP_FILE")

log "Iniciando restore do PostgreSQL"
info "Arquivo: $BACKUP_FILE"
info "Tamanho: $BACKUP_SIZE"
info "Data do backup: $BACKUP_DATE"

# Confirmação de segurança
echo
warning "⚠️  ATENÇÃO: Isso irá SOBRESCREVER todos os dados atuais!"
warning "    Backup atual será perdido se não for feito antes."
echo
read -p "Deseja continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    log "Operação cancelada pelo usuário"
    exit 0
fi

# Criar backup de segurança antes de restaurar
SAFETY_BACKUP="${DB_NAME}-pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
log "Criando backup de segurança: $SAFETY_BACKUP"

if docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > "/tmp/$SAFETY_BACKUP"; then
    log "Backup de segurança criado com sucesso"
else
    warning "Falha ao criar backup de segurança, mas continuando..."
fi

# Descomprimir backup (se necessário)
TEMP_SQL="/tmp/restore_$(date +%s).sql"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Descomprimindo backup..."
    if ! gunzip -c "$BACKUP_FILE" > "$TEMP_SQL"; then
        error "Falha ao descomprimir o arquivo"
        exit 1
    fi
else
    cp "$BACKUP_FILE" "$TEMP_SQL"
fi

# Verificar se o arquivo SQL é válido
if [ ! -s "$TEMP_SQL" ]; then
    error "Arquivo SQL está vazio ou corrompido"
    rm -f "$TEMP_SQL"
    exit 1
fi

# Drop e recriar database (opção mais limpa)
log "Recriando database $DB_NAME..."
docker exec $CONTAINER_NAME psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
docker exec $CONTAINER_NAME psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || true

# Restaurar backup
log "Restaurando dados do backup..."
if docker exec -i $CONTAINER_NAME psql -U $DB_USER $DB_NAME < "$TEMP_SQL"; then
    log "Restore concluído com sucesso!"
else
    error "Falha durante o restore"
    rm -f "$TEMP_SQL"
    exit 1
fi

# Limpar arquivo temporário
rm -f "$TEMP_SQL"

# Verificar integridade dos dados
log "Verificando integridade dos dados..."
TABLE_COUNT=$(docker exec $CONTAINER_NAME psql -U $DB_USER $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
RECORD_COUNT=$(docker exec $CONTAINER_NAME psql -U $DB_USER $DB_NAME -t -c "SELECT COUNT(*) FROM telemetry;" 2>/dev/null | tr -d ' ' || echo "0")

info "Tabelas restauradas: $TABLE_COUNT"
info "Registros de telemetria: $RECORD_COUNT"

# Testar saúde do sistema
log "Testando saúde do sistema..."
if docker exec $CONTAINER_NAME psql -U $DB_USER $DB_USER -c "SELECT 1;" >/dev/null 2>&1; then
    log "Conexão com banco OK"
else
    warning "Problema na conexão com o banco"
fi

# Estatísticas finais
FINAL_SIZE=$(docker exec $CONTAINER_NAME psql -U $DB_USER $DB_USER -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" | tr -d ' ')

log "✅ Restore concluído com sucesso!"
info "Tamanho final do banco: $FINAL_SIZE"
info "Backup de segurança: /tmp/$SAFETY_BACKUP"

# Recomendações
echo
info "📋 Recomendações pós-restore:"
echo "   1. Verifique a UI em http://IP_DO_BOX/"
echo "   2. Confirme se as máquinas aparecem no dashboard"
echo "   3. Verifique se os dados históricos estão consistentes"
echo "   4. Teste a ingestão de novos dados"
echo
warning "Se algo deu errado, restore o backup de segurança:"
warning "  gunzip /tmp/$SAFETY_BACKUP | docker exec -i $CONTAINER_NAME psql -U $DB_USER $DB_NAME"
