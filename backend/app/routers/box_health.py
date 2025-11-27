"""
Router para health monitoring do CNC Telemetry Box.
Mostra status dos serviços e métricas do sistema.
"""

import time
import psutil
from datetime import datetime, timezone
from fastapi import APIRouter
from typing import Dict, Any

from ..db import get_db, engine
from sqlalchemy import text

router = APIRouter(prefix="/box", tags=["box-health"])

# Timestamp de início do serviço
START_TIME = time.time()

def check_database_health() -> str:
    """Verifica se o PostgreSQL está respondendo"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "running"
    except Exception as e:
        print(f"DB health check failed: {e}")
        return "error"

def check_adapter_health() -> str:
    """Verifica se o adapter está enviando dados recentemente"""
    # TODO: Implementar check real via timestamp do último evento
    # Por agora, assume running se backend está up
    return "running"

def check_sync_health() -> str:
    """Verifica se o serviço de sync está ativo"""
    # TODO: Implementar check real via status do sync
    return "running"

def check_frontend_health() -> str:
    """Verifica se o frontend está servindo"""
    # Por enquanto, assume running se estamos respondendo
    return "running"

def get_system_metrics() -> Dict[str, float]:
    """Coleta métricas básicas do sistema"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "memory_total_gb": memory.total / (1024**3),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
            "uptime_seconds": time.time() - START_TIME
        }
    except Exception as e:
        print(f"Error collecting system metrics: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used_gb": 0,
            "memory_total_gb": 0,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "uptime_seconds": time.time() - START_TIME
        }

def get_db_status() -> Dict[str, Any]:
    """Obtém status detalhado do banco de dados"""
    try:
        dialect_name = engine.dialect.name
        
        with engine.connect() as conn:
            if dialect_name == 'postgresql':
                # PostgreSQL específico
                version_result = conn.execute(text("SELECT version()"))
                db_version = version_result.scalar()
                
                tables_result = conn.execute(text("""
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                table_count = tables_result.scalar()
                
                size_result = conn.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """))
                db_size = size_result.scalar()
                
                return {
                    "status": "connected",
                    "dialect": "postgresql",
                    "version": db_version.split(',')[0],
                    "table_count": table_count,
                    "size": db_size
                }
            
            elif dialect_name == 'sqlite':
                # SQLite fallback
                tables_result = conn.execute(text("""
                    SELECT count(*) FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """))
                table_count = tables_result.scalar()
                
                return {
                    "status": "connected",
                    "dialect": "sqlite",
                    "version": "SQLite",
                    "table_count": table_count,
                    "size": "N/A"
                }
            
            else:
                # Outros bancos
                return {
                    "status": "connected",
                    "dialect": dialect_name,
                    "version": "Unknown",
                    "table_count": 0,
                    "size": "N/A"
                }
                
    except Exception as e:
        print(f"Error getting DB status: {e}")
        return {
            "status": "error",
            "dialect": engine.dialect.name if 'engine' in locals() else "unknown",
            "version": None,
            "table_count": 0,
            "size": None,
            "error": str(e)
        }

def get_machine_count_by_state() -> Dict[str, int]:
    """Conta máquinas por estado baseado em heartbeat (running/idle/offline)"""
    try:
        dialect_name = engine.dialect.name
        
        with engine.connect() as conn:
            if dialect_name == 'postgresql':
                # PostgreSQL: usa CTE para obter MAX(ts) por machine_id, depois classifica
                result = conn.execute(text("""
                    WITH machine_last_seen AS (
                        SELECT 
                            machine_id,
                            MAX(ts) as last_seen
                        FROM telemetry 
                        WHERE ts >= NOW() - INTERVAL '24 hours'
                        GROUP BY machine_id
                    )
                    SELECT 
                        CASE 
                            WHEN NOW() - last_seen <= INTERVAL '5 minutes' THEN 'running'
                            WHEN NOW() - last_seen <= INTERVAL '30 minutes' THEN 'idle'
                            ELSE 'offline'
                        END as state,
                        COUNT(machine_id) as count
                    FROM machine_last_seen
                    GROUP BY state
                """))
                
            elif dialect_name == 'sqlite':
                # SQLite: usa subquery com julianday para minutos
                result = conn.execute(text("""
                    WITH machine_last_seen AS (
                        SELECT 
                            machine_id,
                            MAX(ts) as last_seen
                        FROM telemetry 
                        WHERE ts >= datetime('now', '-24 hours')
                        GROUP BY machine_id
                    )
                    SELECT 
                        CASE 
                            WHEN (julianday('now') - julianday(last_seen)) * 24 * 60 <= 5 THEN 'running'
                            WHEN (julianday('now') - julianday(last_seen)) * 24 * 60 <= 30 THEN 'idle'
                            ELSE 'offline'
                        END as state,
                        COUNT(machine_id) as count
                    FROM machine_last_seen
                    GROUP BY state
                """))
            else:
                # Fallback genérico
                result = conn.execute(text("""
                    WITH machine_last_seen AS (
                        SELECT 
                            machine_id,
                            MAX(ts) as last_seen
                        FROM telemetry 
                        WHERE ts >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                        GROUP BY machine_id
                    )
                    SELECT 'offline' as state, COUNT(machine_id) as count
                    FROM machine_last_seen
                """))
            
            # Processar resultados
            state_counts = {'running': 0, 'idle': 0, 'offline': 0}
            for row in result:
                state = row[0]
                count = row[1]
                if state in state_counts:
                    state_counts[state] = count
            
            return state_counts
            
    except Exception as e:
        print(f"Error getting machine count by state: {e}")
        return {'running': 0, 'idle': 0, 'offline': 0, 'error': str(e)}

def get_machine_count() -> Dict[str, int]:
    """Conta máquinas registradas no sistema"""
    try:
        with engine.connect() as conn:
            # Contar máquinas distintas na tabela de telemetria
            telemetry_result = conn.execute(text("""
                SELECT count(DISTINCT machine_id) FROM telemetry
            """))
            telemetry_count = telemetry_result.scalar() or 0
            
            # Contar máquinas na tabela de status (se existir)
            try:
                status_result = conn.execute(text("""
                    SELECT count(DISTINCT machine_id) FROM machine_status
                """))
                status_count = status_result.scalar() or 0
            except:
                status_count = 0
            
            return {
                "total_machines": max(telemetry_count, status_count),
                "telemetry_machines": telemetry_count,
                "status_machines": status_count
            }
    except Exception as e:
        print(f"Error getting machine count: {e}")
        return {
            "total_machines": 0,
            "telemetry_machines": 0,
            "status_machines": 0,
            "error": str(e)
        }

@router.get("/healthz")
def get_box_health() -> Dict[str, Any]:
    """
    Health check completo do Box.
    Retorna status dos serviços e métricas do sistema.
    """
    
    # Status dos serviços
    services = {
        "database": check_database_health(),
        "backend": "running",  # Se estamos respondendo, backend está up
        "adapter": check_adapter_health(),
        "sync": check_sync_health(),
        "frontend": check_frontend_health()
    }
    
    # Métricas do sistema
    system = get_system_metrics()
    
    # Status detalhado do banco
    db_status = get_db_status()
    
    # Contagem de máquinas
    machine_count = get_machine_count()
    
    # Contagem de máquinas por estado (piloto Nestor)
    machine_count_by_state = get_machine_count_by_state()
    
    # Status geral
    all_running = all(status == "running" for status in services.values())
    overall_status = "healthy" if all_running else "degraded"
    
    # Alertas simples
    alerts = []
    if system["cpu_percent"] > 80:
        alerts.append("CPU alta")
    if system["memory_percent"] > 85:
        alerts.append("Memória alta")
    if system["disk_percent"] > 90:
        alerts.append("Disco quase cheio")
    
    return {
        "status": overall_status,
        "version": "v1.0.0",  # TODO: pegar de variável de ambiente
        "box_version": "1.0",  # Nova versão do Box
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "services": services,
        "system": system,
        "db_status": db_status,
        "machine_count": machine_count,
        "machine_count_by_state": machine_count_by_state,
        "alerts": alerts,
        "uptime_formatted": format_uptime(system["uptime_seconds"])
    }

def format_uptime(seconds: float) -> str:
    """Formata uptime em formato legível"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
