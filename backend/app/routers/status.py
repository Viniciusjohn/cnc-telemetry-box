"""
Router para status de máquinas CNC.
Endpoints para consultar e atualizar status individual e geral.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import Field
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "machine_id": "SIM_M80_01",
                "controller_family": "MITSUBISHI_M8X",
                "timestamp_utc": "2025-11-13T10:00:00Z",
                "mode": "AUTOMATIC",
                "execution": "EXECUTING",
                "rpm": 3500,
                "feed_rate": 1200,
                "spindle_load_pct": 52,
                "tool_id": "T03",
                "alarm_code": "105",
                "alarm_message": "OVERTRAVEL +X",
                "part_count": 145,
                "update_interval_ms": 1000,
                "source": "mtconnect:sim"
            }
        }

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
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp_utc": "2025-11-13T10:00:00Z",
                "execution": "EXECUTING",
                "mode": "AUTOMATIC",
                "rpm": 3500,
                "feed_rate": 1200,
                "alarm_code": None,
                "alarm_message": None,
                "part_count": 145
            }
        }

class MachineGridItem(BaseModel):
    """Schema para item de grid de máquinas (resumido)"""
    machine_id: str = Field(..., description="Machine identifier")
    execution: str = Field(..., description="Execution state (EXECUTING, STOPPED, READY)")
    mode: str = Field(..., description="Operating mode (AUTOMATIC, MANUAL, etc.)")
    rpm: float = Field(..., description="Spindle RPM")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    source: str = Field(default="mtconnect:sim", description="Data source identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "machine_id": "SIM_M80_01",
                "execution": "EXECUTING",
                "mode": "AUTOMATIC",
                "rpm": 3500,
                "timestamp_utc": "2025-11-13T10:00:00Z",
                "source": "mtconnect:sim"
            }
        }

# In-memory store (substituir por Redis/DB em produção)
LAST_STATUS: Dict[str, MachineStatus] = {}

@router.get("/{machine_id}/status", response_model=MachineStatus)
def get_machine_status(machine_id: str, response: Response):
    """
    Retorna último status válido da máquina.
    
    Headers canônicos:
    - Cache-Control: no-store (telemetria não deve ser cacheada)
    - Vary: Origin, Accept-Encoding
    - X-Contract-Fingerprint: 010191590cf1
    - Server-Timing: app;dur=<ms>
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Buscar status
    status = LAST_STATUS.get(machine_id)
    
    if not status:
        # Retorno default para máquina sem dados (idle)
        # Permite UI funcionar antes do primeiro /ingest
        status = MachineStatus(
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
    
    return status

@router.get("/{machine_id}/events", response_model=List[MachineEvent])
def get_machine_events(
    machine_id: str, 
    limit: int = Query(50, ge=1, le=200, description="Number of events to return"),
    db: Session = Depends(get_db)
):
    """
    Retorna histórico de eventos da máquina v0.2.
    
    Eventos são ordenados por timestamp_utc desc (mais recentes primeiro).
    Limite padrão: 50 eventos, máximo: 200.
    """
    try:
        events_query = (
            db.query(TelemetryEvents)
            .filter(TelemetryEvents.machine_id == machine_id)
            .order_by(desc(TelemetryEvents.timestamp_utc))
            .limit(limit)
        )
        events = events_query.all()
    except (OperationalError, ProgrammingError) as exc:
        logger.info(
            "events query skipped due to missing table/schema",
            extra={"machine_id": machine_id, "error": str(exc)},
        )
        return []
    except Exception as exc:
        logger.warning(
            "events query failed",
            extra={"machine_id": machine_id, "error": str(exc)},
        )
        return []

    result: List[MachineEvent] = []
    for event in events:
        timestamp = event.timestamp_utc
        ts_str = (
            timestamp.isoformat().replace("+00:00", "Z")
            if hasattr(timestamp, "isoformat")
            else str(timestamp)
        )
        result.append(
            MachineEvent(
                timestamp_utc=ts_str,
                execution=event.execution,
                mode=event.mode,
                rpm=event.rpm,
                feed_rate=event.feed_rate,
                spindle_load_pct=event.spindle_load_pct,
                tool_id=event.tool_id,
                alarm_code=event.alarm_code,
                alarm_message=event.alarm_message,
                part_count=event.part_count,
            )
        )

    return result

@router.get("", response_model=List[str])
def list_machines(response: Response):
    """
    Retorna lista de IDs de máquinas conhecidas.
    
    Machines que já enviaram telemetria pelo menos uma vez.
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Retornar lista de machine_ids do LAST_STATUS
    machine_ids = list(LAST_STATUS.keys())
    machine_ids.sort()  # Ordenar para consistência
    
    return machine_ids

@router.get("/status", response_model=List[MachineGridItem])
def get_machines_status_grid(
    view: str = Query("grid", pattern="^(grid)$", description="View format (only grid supported)"),
    response: Response = None
):
    """
    Retorna status resumido de todas as máquinas para visualização em grid.
    
    Parâmetro view é obrigatório e deve ser 'grid' para futuro extensibilidade.
    Atualiza ~2s para UI em tempo real.
    """
    # Headers canônicos
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Origin, Accept-Encoding"
    response.headers["X-Contract-Fingerprint"] = "010191590cf1"
    response.headers["Server-Timing"] = "app;dur=1"
    
    # Apenas view=grid é suportado
    if view != "grid":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only view=grid is supported")
    
    # Converter LAST_STATUS para MachineGridItem
    grid_items: List[MachineGridItem] = []
    for machine_id, status in LAST_STATUS.items():
        grid_item = MachineGridItem(
            machine_id=status.machine_id,
            execution=status.execution,
            mode=status.mode,
            rpm=status.rpm,
            timestamp_utc=status.timestamp_utc,
            source=status.source
        )
        grid_items.append(grid_item)
    
    # Ordenar por machine_id para consistência
    grid_items.sort(key=lambda x: x.machine_id)
    
    return grid_items

def update_status(
    machine_id: str,
    rpm: float,
    feed_mm_min: float,
    state: str,
    db: Session = None,
    extra: Optional[dict] = None,
    snapshot_ts: Optional[datetime] = None,
):
    """
    Atualiza status no store e persiste evento no histórico.
    Chamado por /ingest após validação.
    """
    # [ASSUNCAO] Mapear state legado para execution v0.1
    execution_map = {
        "running": "EXECUTING",
        "stopped": "STOPPED", 
        "idle": "READY"
    }
    
    timestamp_utc = snapshot_ts or datetime.now(timezone.utc)
    timestamp_str = timestamp_utc.isoformat().replace('+00:00', 'Z')
    execution = execution_map.get(state, "READY")

    spindle_load_pct = None
    alarm_code = None
    if extra:
        spindle_load_pct = extra.get("spindle_load_pct")
        alarm_code = extra.get("alarm_code")
    
    # Atualizar status em memória
    status = MachineStatus(
        machine_id=machine_id,
        controller_family="MITSUBISHI_M8X",
        timestamp_utc=timestamp_str,
        mode="AUTOMATIC",  # [ASSUNCAO] Assumir AUTOMATIC quando recebendo dados
        execution=execution,
        rpm=rpm,
        feed_rate=feed_mm_min,
        spindle_load_pct=spindle_load_pct,
        tool_id=None,  # [ASSUNCAO] Não disponível no payload atual
        alarm_code=alarm_code,
        alarm_message=None,  # [ASSUNCAO] Não disponível no payload atual
        part_count=None,  # [ASSUNCAO] Não disponível no payload atual
        update_interval_ms=1000,
        source="mtconnect:sim"
    )
    
    LAST_STATUS[machine_id] = status
    
    # [v0.2] Persistir evento no histórico (assíncrono/lightweight)
    if db is not None:
        try:
            event = TelemetryEvents(
                machine_id=machine_id,
                timestamp_utc=timestamp_utc,
                mode="AUTOMATIC",
                execution=execution,
                rpm=rpm,
                feed_rate=feed_mm_min,
                spindle_load_pct=spindle_load_pct,
                tool_id=None,
                alarm_code=alarm_code,
                alarm_message=None,
                part_count=None,
                controller_family="MITSUBISHI_M8X",
                source="mtconnect:sim"
            )
            db.add(event)
            db.commit()
        except Exception as e:
            # [ASSUNCAO] Não bloquear o status se falhar o histórico
            print(f"Warning: Failed to persist event to history: {e}")
            db.rollback()
