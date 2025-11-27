"""
Router para status de máquinas CNC - Thread-safe version.
Endpoints para consultar e atualizar status individual e geral.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import OperationalError, ProgrammingError

from ..db import Telemetry, get_db
from ..thread_safe_status import status_manager
from ..logging_config import get_logger

logger = get_logger("status_router")

router = APIRouter(prefix="/v1/machines", tags=["machines"])

class MachineStatus(BaseModel):
    """Schema de status de máquina v0.1 (contrato canônico CNC-Genius)"""
    machine_id: str = Field(..., pattern=r"^[A-Za-z0-9_\-]+$")
    controller_family: str = Field(default="MITSUBISHI_M8X")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    mode: str = Field(..., description="Operating mode (AUTOMATIC, MANUAL, etc.)")
    execution: str = Field(..., description="Execution state (EXECUTING, STOPPED, READY)")
    rpm: float = Field(..., ge=0, le=30000, description="Spindle RPM")
    feed_rate: float | None = Field(None, ge=0, le=10000, description="Feed rate (mm/min)")
    spindle_load_pct: float | None = Field(None, ge=0, le=100, description="Spindle load percentage")
    tool_id: str | None = Field(None, description="Current tool ID")
    alarm_code: str | None = Field(None, description="Active alarm code")
    alarm_message: str | None = Field(None, description="Active alarm message")
    part_count: int | None = Field(None, ge=0, description="Parts produced")
    update_interval_ms: int = Field(default=1000, description="Update interval in milliseconds")
    source: str = Field(default="mtconnect:sim", description="Data source identifier")

class MachineEvent(BaseModel):
    """Schema para eventos de máquina v0.2 (histórico)"""
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    execution: str = Field(..., description="Execution state")
    mode: str | None = Field(None, description="Operating mode")
    rpm: float = Field(..., description="Spindle RPM")
    feed_rate: float | None = Field(None, description="Feed rate (mm/min)")
    spindle_load_pct: float | None = Field(None, description="Spindle load percentage")
    tool_id: str | None = Field(None, description="Tool ID")
    alarm_code: str | None = Field(None, description="Alarm code")
    alarm_message: str | None = Field(None, description="Alarm message")
    part_count: int | None = Field(None, description="Parts produced")

class MachineGridItem(BaseModel):
    """Schema para item de grid de máquinas (resumido)"""
    machine_id: str = Field(..., description="Machine identifier")
    execution: str = Field(..., description="Execution state (EXECUTING, STOPPED, READY)")
    mode: str = Field(..., description="Operating mode (AUTOMATIC, MANUAL, etc.)")
    rpm: float = Field(..., description="Spindle RPM")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    source: str = Field(default="mtconnect:sim", description="Data source identifier")

def update_status(
    machine_id: str,
    rpm: float,
    feed_mm_min: float,
    state: str,
    db: Session = None,
    extra: Optional[dict] = None,
    snapshot_ts: Optional[datetime] = None,
):
    """Atualiza status da máquina de forma thread-safe."""
    
    status_logger = get_logger("status_update", machine_id=machine_id)
    
    try:
        # Mapear estado para execution
        execution_map = {
            "running": "EXECUTING",
            "stopped": "STOPPED",
            "idle": "READY"
        }
        execution = execution_map.get(state, "READY")
        
        # Atualizar status thread-safe
        success = status_manager.update_status(
            machine_id,
            rpm=rpm,
            feed_mm_min=feed_mm_min,
            state=state,
            execution=execution,
            timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            mode="AUTOMATIC",
            controller_mode="AUTOMATIC"
        )
        
        if success:
            status_logger.info(
                "status_updated",
                rpm=rpm,
                feed_mm_min=feed_mm_min,
                state=state,
                execution=execution
            )
        else:
            status_logger.error("status_update_failed")
            
    except Exception as e:
        status_logger.error("status_update_exception", error=str(e), exc_info=True)

@router.get("/{machine_id}/status", response_model=MachineStatus)
def get_machine_status(machine_id: str, response: Response):
    """
    Retorna último status válido da máquina - Thread-safe.
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Buscar status thread-safe
    status_dict = status_manager.get_status(machine_id)
    
    if not status_dict:
        # Retorno default para máquina sem dados (idle)
        status_logger = get_logger("status_default", machine_id=machine_id)
        status_logger.info("returning_default_status")
        
        return MachineStatus(
            machine_id=machine_id,
            controller_family="MITSUBISHI_M8X",
            timestamp_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            mode="MANUAL",
            execution="READY",
            rpm=0.0,
            feed_rate=None,
            spindle_load_pct=None,
            tool_id=None,
            alarm_code=None,
            alarm_message=None,
            part_count=None,
            update_interval_ms=1000,
            source="mtconnect:sim"
        )
    
    # Converter dict para Pydantic model
    return MachineStatus(**status_dict)

@router.get("", response_model=List[str])
def list_machines(response: Response):
    """
    Retorna lista de IDs de máquinas conhecidas - Thread-safe.
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Obter todos os status thread-safe
    all_statuses = status_manager.get_all_statuses()
    machine_ids = [status.get('machine_id', '') for status in all_statuses if status.get('machine_id')]
    machine_ids.sort()  # Ordenar para consistência
    
    logger.info("machines_listed", count=len(machine_ids))
    return machine_ids

@router.get("/status", response_model=List[MachineGridItem])
def get_machines_grid(response: Response):
    """
    Retorna status de todas as máquinas para visualização em grid.
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Obter todos os status thread-safe
    all_statuses = status_manager.get_all_statuses()
    
    grid_items = []
    for status in all_statuses:
        grid_items.append(MachineGridItem(
            machine_id=status.get('machine_id', ''),
            execution=status.get('execution', 'READY'),
            mode=status.get('mode', 'MANUAL'),
            rpm=status.get('rpm', 0.0),
            timestamp_utc=status.get('timestamp', datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')),
            source=status.get('source', 'mtconnect:sim')
        ))
    
    logger.info("grid_status_returned", count=len(grid_items))
    return grid_items

@router.get("/stats")
def get_status_stats():
    """
    Retorna estatísticas do status manager.
    """
    stats = status_manager.get_stats()
    health = status_manager.health_check()
    
    return {
        "stats": stats,
        "health": health,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

@router.post("/cleanup")
def cleanup_old_statuses(max_age_seconds: int = 3600):
    """
    Remove entradas antigas para prevenir memory leaks.
    """
    removed = status_manager.cleanup_old_entries(max_age_seconds)
    
    logger.info("cleanup_completed", removed_count=removed, max_age_seconds=max_age_seconds)
    
    return {
        "removed_entries": removed,
        "max_age_seconds": max_age_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
