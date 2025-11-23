"""FastAPI entrypoint for CNC Telemetry.

Use `app.config.settings` for host/port/database overrides.
"""

import asyncio
import logging

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Import routers
from backend.app.config import ENABLE_M80_WORKER, TELEMETRY_POLL_INTERVAL_SEC
from backend.app.routers import history, oee, status

# Import DB
from backend.app.db import Telemetry, get_db
from backend.app.services.telemetry_pipeline import process_m80_snapshot
from backend.app.services.worker_monitor import (
    mark_worker_enabled,
    mark_snapshot_success,
    mark_snapshot_error,
    get_worker_status,
)

APP_VERSION = "v0.3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("cnc-telemetry")

app = FastAPI(title="CNC Telemetry API", version=APP_VERSION)
_m80_worker_task: asyncio.Task | None = None

# Wire routers
app.include_router(status.router)
app.include_router(history.router)
app.include_router(oee.router)

# CORS
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["Content-Type","X-Request-Id","X-Contract-Fingerprint"],
    expose_headers=["X-Contract-Fingerprint","X-Request-Id","Server-Timing"],
    max_age=600
)

# Enforce preflight 204 (após CORSMiddleware calcular Access-Control-*)
@app.middleware("http")
async def enforce_preflight_204(request: Request, call_next):
    res = await call_next(request)
    # Detecta preflight OPTIONS
    if request.method == "OPTIONS" and request.headers.get("Access-Control-Request-Method"):
        # Copia todos os headers gerados (CORS + canônicos)
        hdrs = {k: v for k, v in res.headers.items()}
        # Remove content-type e content-length para 204
        hdrs.pop("content-type", None)
        hdrs.pop("content-length", None)
        # Retorna 204 sem corpo
        return Response(status_code=204, headers=hdrs, content=b"")
    return res


async def _m80_worker_loop() -> None:
    """Continuously trigger the M80 adapter pipeline respecting config flags."""

    poll_interval = max(0.1, TELEMETRY_POLL_INTERVAL_SEC)
    while True:
        if ENABLE_M80_WORKER:
            try:
                snapshot_ts = datetime.now(timezone.utc)
                process_m80_snapshot()
                mark_snapshot_success(snapshot_ts)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "m80 worker failed to process snapshot",
                    extra={"error": str(exc)},
                )
                mark_snapshot_error()
        await asyncio.sleep(poll_interval)


@app.on_event("startup")
async def log_startup() -> None:
    logger.info("CNC Telemetry API starting", extra={"version": APP_VERSION})
    global _m80_worker_task
    mark_worker_enabled(ENABLE_M80_WORKER)
    if ENABLE_M80_WORKER and _m80_worker_task is None:
        loop = asyncio.get_running_loop()
        _m80_worker_task = loop.create_task(_m80_worker_loop())
        logger.info(
            "M80 telemetry worker scheduled",
            extra={
                "enable_flag": ENABLE_M80_WORKER,
                "poll_interval": TELEMETRY_POLL_INTERVAL_SEC,
            },
        )


@app.on_event("shutdown")
async def stop_workers() -> None:
    global _m80_worker_task
    if _m80_worker_task is not None:
        _m80_worker_task.cancel()
        try:
            await _m80_worker_task
        except asyncio.CancelledError:
            logger.info("M80 telemetry worker cancelled")
        finally:
            _m80_worker_task = None


@app.get("/healthz", tags=["infra"])
async def healthz():
    payload = {
        "status": "ok",
        "service": "cnc-telemetry",
        "version": APP_VERSION,
    }
    payload.update(get_worker_status())
    return payload

@app.middleware("http")
async def headers(req, call_next):
    res = await call_next(req)
    res.headers.update({
        "Cache-Control":"no-store",
        "Vary":"Origin, Accept-Encoding",
        "Server-Timing":"app;dur=1",
        "X-Contract-Fingerprint":"010191590cf1"
    })
    return res

class TelemetryPayload(BaseModel):
    machine_id: str = Field(..., pattern=r"^[a-zA-Z0-9-]+$")
    timestamp: str  # ISO 8601
    rpm: float = Field(..., ge=0, le=30000)
    feed_mm_min: float = Field(..., ge=0, le=10000)
    state: Literal["running", "stopped", "idle"]

@app.post("/v1/telemetry/ingest", status_code=201)
async def ingest_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    """Ingerir dados de telemetria (idempotência: machine_id+timestamp)"""
    
    # Parse timestamp
    ts = datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00'))
    
    # Persistir em TimescaleDB
    try:
        db_record = Telemetry(
            ts=ts,
            machine_id=payload.machine_id,
            rpm=payload.rpm,
            feed_mm_min=payload.feed_mm_min,
            state=payload.state,
            sequence=None  # TODO: extrair do MTConnect se disponível
        )
        db.add(db_record)
        db.commit()
    except Exception as e:
        # Se já existe (duplicate key), apenas atualizar status
        db.rollback()
        print(f"DB insert failed (possibly duplicate): {e}")
    
    # Atualizar status em memória (para /status endpoint) + persistir evento v0.2
    status.update_status(
        machine_id=payload.machine_id,
        rpm=payload.rpm,
        feed_mm_min=payload.feed_mm_min,
        state=payload.state,
        db=db  # [v0.2] Passar sessão DB para persistir histórico
    )
    
    return {
        "ingested": True,
        "machine_id": payload.machine_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

# Endpoint /v1/machines/{id}/status movido para app/routers/status.py
