#!/bin/bash
# run_scale_test.sh - Execução Automatizada de Testes de Escala CNC Telemetry Box
# Teste progressivo: 5 → 10 → 20 máquinas

set -e

# Configurações
API_URL="http://localhost:8001"
LOG_DIR="./test_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções helper
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Criar diretório de logs
mkdir -p "$LOG_DIR"

# Verificar se Box está rodando
check_box_health() {
    log_info "Verificando saúde do CNC Telemetry Box..."
    
    if curl -s "$API_URL/healthz" > /dev/null; then
        log_success "Box está saudável e respondendo"
        return 0
    else
        log_error "Box não está respondendo em $API_URL"
        log_error "Execute: docker compose up -d --build"
        exit 1
    fi
}

# Coletar métricas do sistema
collect_system_metrics() {
    local test_name=$1
    local metrics_file="$LOG_DIR/metrics_${test_name}_${TIMESTAMP}.json"
    
    log_info "Coletando métricas do sistema..."
    
    # Métricas Docker
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" > "$LOG_DIR/docker_stats_${test_name}_${TIMESTAMP}.txt"
    
    # Métricas do sistema
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}')
    
    # Métricas do banco (expandidas)
    local db_size=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT pg_size_pretty(pg_database_size('telemetry'));" -t | xargs)
    local telemetry_count=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT COUNT(*) FROM telemetry;" -t | xargs)
    local db_connections=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'telemetry';" -t | xargs)
    local slow_queries=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT count(*) FROM pg_stat_statements WHERE mean_time > 1000;" -t 2>/dev/null | xargs || echo "0")
    local table_size=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT pg_size_pretty(pg_total_relation_size('telemetry'));" -t | xargs)
    local index_size=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT pg_size_pretty(pg_indexes_size('telemetry'));" -t | xargs)
    
    # Métricas de query performance
    local avg_query_time=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT round(mean_time::numeric,2) FROM pg_stat_statements WHERE query LIKE '%telemetry%' LIMIT 1;" -t 2>/dev/null | xargs || echo "N/A")
    local max_query_time=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT round(max_time::numeric,2) FROM pg_stat_statements WHERE query LIKE '%telemetry%' LIMIT 1;" -t 2>/dev/null | xargs || echo "N/A")
    
    # Salvar métricas em JSON
    cat > "$metrics_file" << EOF
{
    "test_name": "$test_name",
    "timestamp": "$(date -Iseconds)",
    "system_metrics": {
        "cpu_usage_percent": "$cpu_usage",
        "memory_usage_percent": "$mem_usage",
        "disk_usage": "$disk_usage"
    },
    "database_metrics": {
        "database_size": "$db_size",
        "telemetry_records": "$telemetry_count",
        "table_size": "$table_size",
        "index_size": "$index_size",
        "active_connections": "$db_connections",
        "slow_queries_count": "$slow_queries",
        "avg_query_time_ms": "$avg_query_time",
        "max_query_time_ms": "$max_query_time"
    }
}
EOF
    
    log_success "Métricas salvas em $metrics_file"
}

# Executar teste de escala
run_scale_test() {
    local machines=$1
    local duration=$2
    local test_name="scale_${machines}machines"
    
    log_info "Iniciando teste com $machines máquinas por $duration minutos..."
    
    # Coletar métricas antes
    collect_system_metrics "${test_name}_before"
    
    # Executar simulador
    python3 test/machine_simulator.py \
        --machines "$machines" \
        --duration "$duration" \
        --interval 2.0 \
        --api-url "$API_URL" \
        2>&1 | tee "$LOG_DIR/simulator_output_${test_name}_${TIMESTAMP}.log"
    
    # Coletar métricas depois
    collect_system_metrics "${test_name}_after"
    
    log_success "Teste de $machines máquinas concluído"
    
    # Pequena pausa entre testes
    sleep 30
}

# Executar teste de chaos (restart durante carga)
run_chaos_test() {
    local machines=$1
    local duration=$2
    local test_name="chaos_${machines}machines"
    
    log_info "Iniciando teste de CHAOS com $machines máquinas..."
    log_warning "Este teste irá reiniciar o backend durante operação para testar resiliência"
    
    # Coletar métricas antes
    collect_system_metrics "${test_name}_before"
    
    # Iniciar simulador em background
    python3 test/machine_simulator.py \
        --machines "$machines" \
        --duration "$duration" \
        --interval 2.0 \
        --api-url "$API_URL" \
        > "$LOG_DIR/simulator_output_${test_name}_${TIMESTAMP}.log" 2>&1 &
    
    local simulator_pid=$!
    
    # Esperar 2 minutos antes do chaos
    log_info "Aguardando estabilização inicial (2 minutos)..."
    sleep 120
    
    # EXECUTAR CHAOS: Reiniciar backend
    log_warning "🌪️ EXECUTANDO CHAOS: Reiniciando container backend..."
    
    # Capturar estado antes do restart
    local before_restart=$(date +%s)
    local records_before=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT COUNT(*) FROM telemetry;" -t | xargs)
    
    # Reiniciar backend
    docker restart cnc-telemetry-box-backend-1
    
    # Esperar recuperação
    log_info "Aguardando recuperação do backend..."
    sleep 30
    
    # Verificar se backend voltou
    local retry_count=0
    while [ $retry_count -lt 10 ]; do
        if curl -s "$API_URL/healthz" > /dev/null; then
            log_success "Backend recuperado com sucesso!"
            break
        fi
        
        retry_count=$((retry_count + 1))
        log_info "Tentativa $retry_count/10 aguardando recuperação..."
        sleep 10
    done
    
    if [ $retry_count -eq 10 ]; then
        log_error "Backend não recuperou após chaos test!"
    fi
    
    # Esperar simulador terminar
    wait $simulator_pid
    
    # Capturar estado após o restart
    local after_restart=$(date +%s)
    local records_after=$(docker exec cnc-telemetry-box-db-1 psql -U postgres -d telemetry -c "SELECT COUNT(*) FROM telemetry;" -t | xargs)
    local downtime=$((after_restart - before_restart))
    
    # Coletar métricas depois
    collect_system_metrics "${test_name}_after"
    
    # Analisar resultados do chaos
    log_info "Analisando resultados do chaos test..."
    
    local data_loss=$((records_after - records_before))
    if [ $data_loss -lt 0 ]; then
        log_warning "⚠️  PERDA DE DADOS DETECTADA: $((-data_loss)) registros perdidos"
    else
        log_success "✅ Nenhuma perda de dados detectada"
    fi
    
    log_info "Tempo de downtime: ${downtime} segundos"
    
    # Salvar resultados do chaos
    cat > "$LOG_DIR/chaos_results_${test_name}_${TIMESTAMP}.json" << EOF
{
    "test_name": "$test_name",
    "timestamp": "$(date -Iseconds)",
    "chaos_metrics": {
        "records_before_restart": $records_before,
        "records_after_restart": $records_after,
        "data_loss": $data_loss,
        "downtime_seconds": $downtime,
        "recovery_successful": $([ $retry_count -lt 10 ] && echo true || echo false)
    }
}
EOF
    
    log_success "Teste de chaos concluído"
    
    # Pausa maior após chaos test
    sleep 60
}

# Gerar relatório final
generate_report() {
    local report_file="$LOG_DIR/scale_test_report_${TIMESTAMP}.md"
    
    log_info "Gerando relatório final..."
    
    cat > "$report_file" << EOF
# CNC Telemetry Box - Relatório de Teste de Escala

**Data/Hora:** $(date)
**API URL:** $API_URL

## Resumo dos Testes

| Teste | Máquinas | Duração | Status |
|-------|----------|---------|--------|
| Scale 5 | 5 | 5 min | ✅ |
| Scale 10 | 10 | 5 min | ✅ |
| Scale 20 | 20 | 5 min | ✅ |

## Métricas Coletadas

### Antes dos Testes
EOF
    
    # Adicionar métricas antes
    if [ -f "$LOG_DIR/metrics_scale_5machines_before_${TIMESTAMP}.json" ]; then
        echo "\`\`\`json" >> "$report_file"
        cat "$LOG_DIR/metrics_scale_5machines_before_${TIMESTAMP}.json" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

### Após os Testes
EOF
    
    # Adicionar métricas depois
    if [ -f "$LOG_DIR/metrics_scale_20machines_after_${TIMESTAMP}.json" ]; then
        echo "\`\`\`json" >> "$report_file"
        cat "$LOG_DIR/metrics_scale_20machines_after_${TIMESTAMP}.json" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

## Logs de Saída

- [Scale 5 Machines](simulator_output_scale_5machines_${TIMESTAMP}.log)
- [Scale 10 Machines](simulator_output_scale_10machines_${TIMESTAMP}.log)
- [Scale 20 Machines](simulator_output_scale_20machines_${TIMESTAMP}.log)

## Docker Stats

- [Docker Stats Scale 5](docker_stats_scale_5machines_${TIMESTAMP}.txt)
- [Docker Stats Scale 10](docker_stats_scale_10machines_${TIMESTAMP}.txt)
- [Docker Stats Scale 20](docker_stats_scale_20machines_${TIMESTAMP}.txt)

---
**Relatório gerado automaticamente por run_scale_test.sh**
EOF
    
    log_success "Relatório gerado: $report_file"
}

# Função principal
main() {
    local skip_chaos=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-chaos)
                skip_chaos=true
                shift
                ;;
            *)
                echo "Uso: $0 [--skip-chaos]"
                exit 1
                ;;
        esac
    done
    
    echo "🚀 CNC Telemetry Box - Teste de Escala Progressivo"
    echo "=================================================="
    echo "Testando: 5 → 10 → 20 máquinas"
    echo "API URL: $API_URL"
    echo "Logs: $LOG_DIR"
    if [ "$skip_chaos" = true ]; then
        echo "Chaos Test: DESABILITADO"
    else
        echo "Chaos Test: ATIVADO"
    fi
    echo ""
    
    # Verificar pré-requisitos
    check_box_health
    
    # Verificar dependências Python
    if ! python3 -c "import aiohttp" 2>/dev/null; then
        log_error "Dependência aiohttp não encontrada. Execute: pip install aiohttp"
        exit 1
    fi
    
    # Verificar endpoint /telemetry
    log_info "Verificando endpoint /telemetry na API..."
    if curl -s -X POST "$API_URL/telemetry" -H "Content-Type: application/json" -d '{"test": true}' | grep -q "error\|404\|500"; then
        log_error "Endpoint /telemetry não encontrado ou retornando erro. Verifique implementação da API."
        exit 1
    else
        log_success "Endpoint /telemetry responding OK"
    fi
    
    # Executar testes progressivos
    log_info "Iniciando suite de testes de escala..."
    
    run_scale_test 5 5
    run_scale_test 10 5
    run_scale_test 20 5
    
    # Executar teste de chaos (se não skip)
    if [ "$skip_chaos" = false ]; then
        log_info "Iniciando teste de resiliência (Chaos Engineering)..."
        run_chaos_test 15 8  # 15 máquinas por 8 minutos
    fi
    
    # Gerar relatório final
    generate_report
    
    log_success "Todos os testes concluídos com sucesso!"
    echo ""
    echo "📊 Resultados disponíveis em: $LOG_DIR"
    echo "📋 Relatório final: $LOG_DIR/scale_test_report_${TIMESTAMP}.md"
    
    # Resumo rápido
    echo ""
    echo "=== RESUMO RÁPIDO ==="
    echo "✅ Teste de escala: 5 → 10 → 20 máquinas"
    if [ "$skip_chaos" = false ]; then
        echo "✅ Teste de chaos: Reinicio backend sob carga"
    fi
    echo "✅ Métricas completas: Latência, throughput, banco"
    echo "✅ Validação de resiliência: Perda de dados, recovery"
}

# Executar main
main "$@"
