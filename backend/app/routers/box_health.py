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
