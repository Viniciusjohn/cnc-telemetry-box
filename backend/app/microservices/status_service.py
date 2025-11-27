"""
Status Microservice - Handles machine status management and queries.
Part of microservices architecture for CNC Telemetry Box.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

from ..logging_config import get_logger, log_function_call
from ..thread_safe_status import status_manager
from ..dependency_injection import injectable, IStatusService, container
from ..message_queue import Message, queue_manager, QueueNames
from ..event_bus import event_bus, MachineStatusChanged

logger = get_logger("status_service")

# Pydantic models
class MachineStatusResponse(BaseModel):
    machine_id: str
    rpm: float
    feed_mm_min: float
    state: str
    execution: str
    mode: str
    timestamp: str
    last_updated: str
    update_count: int

class MachineListResponse(BaseModel):
    machines: List[str]
    count: int
    timestamp: str

class StatusUpdateRequest(BaseModel):
    machine_id: str
    rpm: float = Field(..., ge=0, le=30000)
    feed_mm_min: float = Field(..., ge=0, le=10000)
    state: str = Field(..., regex=r"^(running|stopped|idle)$")
    mode: str = Field(default="AUTOMATIC")
    execution: str = Field(default="READY")

class StatusUpdateResponse(BaseModel):
    success: bool
    machine_id: str
    updated_at: str
    previous_state: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    machine_count: int
    total_updates: int
    uptime_seconds: float

# Status service implementation
@injectable(IStatusService)
class StatusMicroService(IStatusService):
    """Status microservice implementation."""
    
    def __init__(self):
        self.start_time = time.time()
        self.logger = get_logger("status_microservice")
    
    async def update_status(self, machine_id: str, status: Dict[str, Any]) -> bool:
        """Update machine status."""
        try:
            # Get current status for change detection
            current_status = status_manager.get_status(machine_id)
            old_state = current_status.get("state") if current_status else None
            
            # Update status
            success = status_manager.update_status(machine_id, **status)
            
            if success and old_state != status.get("state"):
                # Emit status change event
                event = MachineStatusChanged(
                    machine_id=machine_id,
                    old_state=old_state or "unknown",
                    new_state=status.get("state", "unknown"),
                    change_reason="telemetry_update"
                )
                
                await event_bus.publish(event)
                
                self.logger.info(
                    "status_changed",
                    machine_id=machine_id,
                    old_state=old_state,
                    new_state=status.get("state")
                )
            
            return success
            
        except Exception as e:
            self.logger.error("status_update_error", machine_id=machine_id, error=str(e), exc_info=True)
            return False
    
    async def get_status(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get machine status."""
        try:
            return status_manager.get_status(machine_id)
        except Exception as e:
            self.logger.error("status_get_error", machine_id=machine_id, error=str(e), exc_info=True)
            return None
    
    async def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Get all machine statuses."""
        try:
            return status_manager.get_all_statuses()
        except Exception as e:
            self.logger.error("get_all_statuses_error", error=str(e), exc_info=True)
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return status_manager.get_stats()

# FastAPI app
app = FastAPI(
    title="Status Microservice",
    description="CNC Telemetry Box - Machine Status Service",
    version="1.0.0"
)

# Service instance
status_service = container.resolve(IStatusService)

@app.get("/machines/{machine_id}/status", response_model=MachineStatusResponse)
@log_function_call
async def get_machine_status(machine_id: str):
    """Get machine status."""
    
    request_logger = get_logger("get_machine_status", machine_id=machine_id)
    
    try:
        status = await status_service.get_status(machine_id)
        
        if not status:
            # Return default status
            default_status = {
                "machine_id": machine_id,
                "rpm": 0.0,
                "feed_mm_min": 0.0,
                "state": "idle",
                "execution": "READY",
                "mode": "MANUAL",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "update_count": 0
            }
            
            request_logger.info("default_status_returned")
            return MachineStatusResponse(**default_status)
        
        return MachineStatusResponse(**status)
        
    except Exception as e:
        request_logger.error("get_status_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get machine status")

@app.get("/machines", response_model=MachineListResponse)
@log_function_call
async def list_machines():
    """List all machines."""
    
    try:
        statuses = await status_service.get_all_statuses()
        machine_ids = [status.get("machine_id", "") for status in statuses if status.get("machine_id")]
        machine_ids.sort()
        
        return MachineListResponse(
            machines=machine_ids,
            count=len(machine_ids),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error("list_machines_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list machines")

@app.get("/machines/status")
@log_function_call
async def get_all_machine_statuses():
    """Get all machine statuses."""
    
    try:
        statuses = await status_service.get_all_statuses()
        
        return {
            "machines": statuses,
            "count": len(statuses),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("get_all_statuses_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get machine statuses")

@app.post("/machines/{machine_id}/status", response_model=StatusUpdateResponse)
@log_function_call
async def update_machine_status(machine_id: str, request: StatusUpdateRequest):
    """Update machine status."""
    
    request_logger = get_logger("update_machine_status", machine_id=machine_id)
    
    try:
        # Get current state
        current_status = await status_service.get_status(machine_id)
        previous_state = current_status.get("state") if current_status else None
        
        # Update status
        status_data = request.dict()
        status_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        success = await status_service.update_status(machine_id, status_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update machine status")
        
        response = StatusUpdateResponse(
            success=True,
            machine_id=machine_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
            previous_state=previous_state
        )
        
        request_logger.info("status_updated", previous_state=previous_state, new_state=request.state)
        return response
        
    except Exception as e:
        request_logger.error("update_status_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update machine status")

@app.get("/health", response_model=HealthResponse)
@log_function_call
async def health_check():
    """Health check endpoint."""
    
    try:
        stats = status_service.get_stats()
        uptime = time.time() - status_service.start_time
        
        # Determine health status
        machine_count = stats.get("machine_count", 0)
        total_updates = stats.get("total_updates", 0)
        
        if machine_count == 0 and uptime > 60:  # No machines after 1 minute
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthResponse(
            status=status,
            service="status",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            machine_count=machine_count,
            total_updates=total_updates,
            uptime_seconds=uptime
        )
        
    except Exception as e:
        logger.error("health_check_error", error=str(e), exc_info=True)
        return HealthResponse(
            status="unhealthy",
            service="status",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            machine_count=0,
            total_updates=0,
            uptime_seconds=0
        )

@app.get("/stats")
@log_function_call
async def get_service_stats():
    """Get detailed service statistics."""
    
    try:
        status_stats = status_service.get_stats()
        health = status_manager.health_check()
        
        return {
            "status_service": {
                "uptime_seconds": time.time() - status_service.start_time,
                **status_stats
            },
            "status_manager": health,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("get_stats_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@app.post("/admin/cleanup")
@log_function_call
async def cleanup_old_statuses(max_age_seconds: int = Query(default=3600, ge=60)):
    """Cleanup old status entries."""
    
    try:
        removed = status_manager.cleanup_old_entries(max_age_seconds)
        
        logger.info("cleanup_completed", removed_count=removed, max_age_seconds=max_age_seconds)
        
        return {
            "removed_entries": removed,
            "max_age_seconds": max_age_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("cleanup_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cleanup old statuses")

@app.post("/admin/reset")
@log_function_call
async def reset_all_statuses():
    """Reset all status data (admin only)."""
    
    try:
        # This would need to be implemented in the status manager
        # For now, just log the request
        logger.warning("reset_all_statuses_requested")
        
        return {
            "message": "Status reset functionality not implemented",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("reset_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset statuses")

# Background task to process status updates from queue
async def process_status_queue():
    """Background task to process status updates from queue."""
    
    processor_logger = get_logger("status_queue_processor")
    
    async def process_message(message: Message):
        """Process individual status update message."""
        try:
            payload = message.payload
            
            # Update status
            await status_service.update_status(
                payload["machine_id"],
                payload["status_data"]
            )
            
            processor_logger.debug(
                "status_message_processed",
                machine_id=payload["machine_id"],
                message_id=message.id
            )
            
        except Exception as e:
            processor_logger.error(
                "status_message_processing_failed",
                message_id=message.id,
                error=str(e),
                exc_info=True
            )
    
    # Process messages continuously
    from ..message_queue import process_queue_messages
    await process_queue_messages(
        QueueNames.STATUS_UPDATES,
        process_message,
        batch_size=10,
        timeout=1.0
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize status service."""
    logger.info("status_service_starting")
    
    # Start event bus
    await event_bus.start()
    
    # Start queue processor
    asyncio.create_task(process_status_queue())
    
    logger.info("status_service_started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup status service."""
    logger.info("status_service_stopping")
    
    # Stop event bus
    await event_bus.stop()
    
    logger.info("status_service_stopped")

# Main function for running service
def main():
    """Run status microservice."""
    logger.info("starting_status_microservice")
    
    uvicorn.run(
        "status_service:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
