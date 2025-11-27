"""
Telemetry Microservice - Handles all telemetry ingestion and processing.
Part of microservices architecture for CNC Telemetry Box.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn

from ..logging_config import get_logger, log_function_call
from ..circuit_breaker import circuit_breaker, mtconnect_fallback
from ..message_queue import Message, queue_manager, QueueNames
from ..event_bus import event_bus, TelemetryReceived
from ..dependency_injection import injectable, ITelemetryService, container

logger = get_logger("telemetry_service")

# Pydantic models
class TelemetryPayload(BaseModel):
    machine_id: str = Field(..., pattern=r"^[a-zA-Z0-9-]+$")
    timestamp: str  # ISO 8601
    rpm: float = Field(..., ge=0, le=30000)
    feed_mm_min: float = Field(..., ge=0, le=10000)
    state: str = Field(..., regex=r"^(running|stopped|idle)$")
    source: str = Field(default="mtconnect")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TelemetryResponse(BaseModel):
    success: bool
    message_id: str
    machine_id: str
    processed_at: str
    queue_position: Optional[int] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    processed_count: int
    error_count: int
    queue_size: int

# Telemetry service implementation
@injectable(ITelemetryService)
class TelemetryMicroService(ITelemetryService):
    """Telemetry microservice implementation."""
    
    def __init__(self):
        self.start_time = time.time()
        self.processed_count = 0
        self.error_count = 0
        self.logger = get_logger("telemetry_microservice")
    
    async def process_telemetry(self, machine_id: str, data: Dict[str, Any]) -> bool:
        """Process telemetry data."""
        try:
            # Validate data
            self._validate_telemetry_data(machine_id, data)
            
            # Create message for queue
            message = Message(
                payload={
                    "machine_id": machine_id,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                headers={
                    "service": "telemetry",
                    "version": "1.0"
                },
                priority=1  # Normal priority
            )
            
            # Enqueue for processing
            success = await queue_manager.enqueue(QueueNames.TELEMETRY_INGEST, message)
            
            if success:
                self.processed_count += 1
                self.logger.info("telemetry_queued", machine_id=machine_id, message_id=message.id)
                return True
            else:
                self.error_count += 1
                self.logger.error("telemetry_queue_failed", machine_id=machine_id)
                return False
                
        except Exception as e:
            self.error_count += 1
            self.logger.error("telemetry_processing_error", machine_id=machine_id, error=str(e), exc_info=True)
            return False
    
    def _validate_telemetry_data(self, machine_id: str, data: Dict[str, Any]) -> None:
        """Validate telemetry data."""
        required_fields = ["rpm", "feed_mm_min", "state", "timestamp"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate ranges
        if not (0 <= data["rpm"] <= 30000):
            raise ValueError(f"RPM out of range: {data['rpm']}")
        
        if not (0 <= data["feed_mm_min"] <= 10000):
            raise ValueError(f"Feed rate out of range: {data['feed_mm_min']}")
        
        if data["state"] not in ["running", "stopped", "idle"]:
            raise ValueError(f"Invalid state: {data['state']}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        uptime = time.time() - self.start_time
        
        return {
            "service": "telemetry",
            "uptime_seconds": uptime,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "error_rate": (self.error_count / max(self.processed_count, 1)) * 100,
            "messages_per_second": self.processed_count / max(uptime, 1)
        }

# FastAPI app
app = FastAPI(
    title="Telemetry Microservice",
    description="CNC Telemetry Box - Telemetry Processing Service",
    version="1.0.0"
)

# Service instance
telemetry_service = container.resolve(ITelemetryService)

@app.post("/telemetry/ingest", response_model=TelemetryResponse)
@log_function_call
async def ingest_telemetry(
    payload: TelemetryPayload,
    background_tasks: BackgroundTasks,
    request: Request
):
    """Ingest telemetry data."""
    
    request_logger = get_logger("telemetry_ingest", machine_id=payload.machine_id)
    
    try:
        # Process telemetry
        data = payload.dict()
        success = await telemetry_service.process_telemetry(payload.machine_id, data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to process telemetry")
        
        # Get queue position
        queue_size = await queue_manager.size(QueueNames.TELEMETRY_INGEST)
        
        # Emit event for real-time processing
        event = TelemetryReceived(
            machine_id=payload.machine_id,
            rpm=payload.rpm,
            feed_mm_min=payload.feed_mm_min,
            state=payload.state,
            timestamp_utc=payload.timestamp
        )
        
        # Add event to background tasks
        background_tasks.add_task(event_bus.publish, event)
        
        response = TelemetryResponse(
            success=True,
            message_id=str(time.time()),  # Simple ID for now
            machine_id=payload.machine_id,
            processed_at=datetime.now(timezone.utc).isoformat(),
            queue_position=queue_size
        )
        
        request_logger.info("telemetry_ingested", queue_size=queue_size)
        return response
        
    except ValueError as e:
        request_logger.error("validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        request_logger.error("ingest_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/telemetry/batch", response_model=List[TelemetryResponse])
@log_function_call
async def ingest_batch_telemetry(
    payloads: List[TelemetryPayload],
    background_tasks: BackgroundTasks
):
    """Ingest multiple telemetry messages."""
    
    if len(payloads) > 100:
        raise HTTPException(status_code=400, detail="Batch size too large (max 100)")
    
    responses = []
    
    for payload in payloads:
        try:
            data = payload.dict()
            success = await telemetry_service.process_telemetry(payload.machine_id, data)
            
            if success:
                response = TelemetryResponse(
                    success=True,
                    message_id=str(time.time()),
                    machine_id=payload.machine_id,
                    processed_at=datetime.now(timezone.utc).isoformat()
                )
                responses.append(response)
            else:
                responses.append(TelemetryResponse(
                    success=False,
                    message_id="",
                    machine_id=payload.machine_id,
                    processed_at=datetime.now(timezone.utc).isoformat()
                ))
                
        except Exception as e:
            logger.error("batch_item_error", machine_id=payload.machine_id, error=str(e))
            responses.append(TelemetryResponse(
                success=False,
                message_id="",
                machine_id=payload.machine_id,
                processed_at=datetime.now(timezone.utc).isoformat()
            ))
    
    return responses

@app.get("/health", response_model=HealthResponse)
@log_function_call
async def health_check():
    """Health check endpoint."""
    
    stats = telemetry_service.get_stats()
    queue_size = await queue_manager.size(QueueNames.TELEMETRY_INGEST)
    
    # Determine health status
    error_rate = stats["error_rate"]
    if error_rate > 10:
        status = "unhealthy"
    elif error_rate > 5:
        status = "degraded"
    else:
        status = "healthy"
    
    return HealthResponse(
        status=status,
        service="telemetry",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=stats["uptime_seconds"],
        processed_count=stats["processed_count"],
        error_count=stats["error_count"],
        queue_size=queue_size
    )

@app.get("/stats")
@log_function_call
async def get_service_stats():
    """Get detailed service statistics."""
    
    telemetry_stats = telemetry_service.get_stats()
    queue_stats = await queue_manager.get_stats()
    
    return {
        "telemetry": telemetry_stats,
        "queues": queue_stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/admin/reset-stats")
@log_function_call
async def reset_stats():
    """Reset service statistics (admin only)."""
    
    telemetry_service.processed_count = 0
    telemetry_service.error_count = 0
    
    logger.info("stats_reset")
    
    return {"message": "Statistics reset successfully"}

# Background task to process queued messages
async def process_telemetry_queue():
    """Background task to process telemetry from queue."""
    
    processor_logger = get_logger("telemetry_queue_processor")
    
    async def process_message(message: Message):
        """Process individual telemetry message."""
        try:
            payload = message.payload
            
            # Update status service
            from ..dependency_injection import IStatusService
            status_service = container.resolve(IStatusService)
            
            await status_service.update_status(
                payload["machine_id"],
                {
                    "rpm": payload["data"]["rpm"],
                    "feed_mm_min": payload["data"]["feed_mm_min"],
                    "state": payload["data"]["state"],
                    "timestamp": payload["data"]["timestamp"]
                }
            )
            
            processor_logger.debug(
                "telemetry_message_processed",
                machine_id=payload["machine_id"],
                message_id=message.id
            )
            
        except Exception as e:
            processor_logger.error(
                "telemetry_message_processing_failed",
                message_id=message.id,
                error=str(e),
                exc_info=True
            )
    
    # Process messages continuously
    from ..message_queue import process_queue_messages
    await process_queue_messages(
        QueueNames.TELEMETRY_INGEST,
        process_message,
        batch_size=5,
        timeout=1.0
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize telemetry service."""
    logger.info("telemetry_service_starting")
    
    # Start event bus
    await event_bus.start()
    
    # Start queue processor
    asyncio.create_task(process_telemetry_queue())
    
    logger.info("telemetry_service_started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup telemetry service."""
    logger.info("telemetry_service_stopping")
    
    # Stop event bus
    await event_bus.stop()
    
    logger.info("telemetry_service_stopped")

# Main function for running service
def main():
    """Run telemetry microservice."""
    logger.info("starting_telemetry_microservice")
    
    uvicorn.run(
        "telemetry_service:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
