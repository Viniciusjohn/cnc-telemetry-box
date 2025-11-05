from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

app = FastAPI()

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
async def ingest_telemetry(payload: TelemetryPayload):
    """Ingerir dados de telemetria (idempotência: machine_id+timestamp)"""
    # TODO: Persistir em DB (validar duplicatas por machine_id+timestamp)
    return {
        "ingested": True,
        "machine_id": payload.machine_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/v1/machines/{mid}/status")
def status(mid:str): 
    return {"machine_id": mid, "rpm": 4200, "feed_mm_min": 850, "running": True,
            "stopped": False, "last_update": datetime.utcnow().isoformat()+"Z",
            "session":{"machining_time_sec":1378,"stopped_time_sec":42}}
