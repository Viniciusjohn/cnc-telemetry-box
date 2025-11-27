"""
Event Bus implementation for decoupled architecture.
Publish-subscribe pattern for internal communication.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Callable, Any, Type, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
import logging
from abc import ABC, abstractmethod

from ..logging_config import get_logger

logger = get_logger("event_bus")

class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Event:
    """Base event class."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "event_type": self.__class__.__name__
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        # Remove event_type from metadata if present
        metadata = data.get("metadata", {})
        metadata.pop("event_type", None)
        
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            source=data.get("source", "unknown"),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            correlation_id=data.get("correlation_id"),
            metadata=metadata
        )

# Domain Events
@dataclass
class TelemetryReceived(Event):
    """Event when new telemetry data is received."""
    machine_id: str
    rpm: float
    feed_mm_min: float
    state: str
    timestamp_utc: str
    
    def __post_init__(self):
        self.source = "telemetry_ingest"
        self.priority = EventPriority.NORMAL

@dataclass
class MachineStatusChanged(Event):
    """Event when machine status changes."""
    machine_id: str
    old_state: str
    new_state: str
    change_reason: str = "automatic"
    
    def __post_init__(self):
        self.source = "status_manager"
        self.priority = EventPriority.HIGH

@dataclass
class AlertTriggered(Event):
    """Event when an alert is triggered."""
    machine_id: str
    alert_type: str
    severity: str
    message: str
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None
    
    def __post_init__(self):
        self.source = "alert_system"
        self.priority = EventPriority.HIGH if severity in ["critical", "error"] else EventPriority.NORMAL

@dataclass
class BackupCompleted(Event):
    """Event when backup operation completes."""
    backup_file: str
    size_bytes: int
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.source = "backup_service"
        self.priority = EventPriority.NORMAL

@dataclass
class SystemHealthCheck(Event):
    """Event for system health monitoring."""
    component: str
    status: str  # "healthy", "degraded", "error"
    metrics: Dict[str, Any]
    timestamp_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        self.source = "health_monitor"
        self.priority = EventPriority.CRITICAL if status == "error" else EventPriority.NORMAL

class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle the event."""
        pass
    
    @property
    @abstractmethod
    def handled_events(self) -> List[Type[Event]]:
        """List of event types this handler can handle."""
        pass

class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def __init__(self, max_queue_size: int = 10000):
        self._handlers: Dict[Type[Event], List[EventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_registered": 0,
            "queue_size": 0
        }
        self.logger = get_logger("event_bus")
    
    def subscribe(self, handler: EventHandler) -> None:
        """Subscribe handler to events."""
        for event_type in handler.handled_events:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            self._stats["handlers_registered"] += 1
        
        self.logger.info("handler_subscribed", handler=handler.__class__.__name__, events=[e.__name__ for e in handler.handled_events])
    
    def unsubscribe(self, handler: EventHandler) -> None:
        """Unsubscribe handler from events."""
        for event_type in handler.handled_events:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    self._stats["handlers_registered"] -= 1
                except ValueError:
                    pass
        
        self.logger.info("handler_unsubscribed", handler=handler.__class__.__name__)
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        try:
            await self._event_queue.put(event)
            self._stats["events_published"] += 1
            
            self.logger.debug(
                "event_published",
                event_type=event.__class__.__name__,
                event_id=event.event_id,
                source=event.source
            )
        except asyncio.QueueFull:
            self.logger.error("event_queue_full", event_type=event.__class__.__name__)
            self._stats["events_failed"] += 1
            raise
    
    async def publish_batch(self, events: List[Event]) -> None:
        """Publish multiple events efficiently."""
        for event in events:
            await self.publish(event)
    
    async def start(self) -> None:
        """Start event bus processing."""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        self.logger.info("event_bus_started")
    
    async def stop(self) -> None:
        """Stop event bus processing."""
        if not self._running:
            return
        
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("event_bus_stopped")
    
    async def _process_events(self) -> None:
        """Process events from queue."""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                
                # Update stats
                self._stats["queue_size"] = self._event_queue.qsize()
                
                # Find handlers for this event type
                event_type = type(event)
                handlers = self._handlers.get(event_type, [])
                
                if not handlers:
                    self.logger.warning("no_handlers_for_event", event_type=event_type.__name__)
                    continue
                
                # Execute all handlers concurrently
                tasks = [self._safe_handle(handler, event) for handler in handlers]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(
                            "handler_failed",
                            handler=handlers[i].__class__.__name__,
                            event_type=event_type.__name__,
                            error=str(result)
                        )
                        self._stats["events_failed"] += 1
                    else:
                        self._stats["events_processed"] += 1
                
                self.logger.debug(
                    "event_processed",
                    event_type=event_type.__name__,
                    handlers_count=len(handlers),
                    success_count=sum(1 for r in results if not isinstance(r, Exception))
                )
                
            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except Exception as e:
                self.logger.error("event_processing_error", error=str(e), exc_info=True)
                await asyncio.sleep(1)  # Prevent tight loop on errors
    
    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        """Safely execute event handler."""
        try:
            await handler.handle(event)
        except Exception as e:
            self.logger.error(
                "handler_exception",
                handler=handler.__class__.__name__,
                event_type=event.__class__.__name__,
                error=str(e),
                exc_info=True
            )
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        self._stats["queue_size"] = self._event_queue.qsize()
        self._stats["running"] = self._running
        
        return {
            **self._stats,
            "registered_handlers": {
                event_type.__name__: len(handlers)
                for event_type, handlers in self._handlers.items()
            }
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get event bus health status."""
        stats = self.get_stats()
        
        # Determine health based on queue size and error rate
        queue_health = "healthy" if stats["queue_size"] < 1000 else "degraded" if stats["queue_size"] < 5000 else "error"
        error_rate = (stats["events_failed"] / max(stats["events_published"], 1)) * 100
        error_health = "healthy" if error_rate < 1 else "degraded" if error_rate < 5 else "error"
        
        overall_health = "healthy" if queue_health == "healthy" and error_health == "healthy" else "degraded" if queue_health != "error" and error_health != "error" else "error"
        
        return {
            "status": overall_health,
            "queue_health": queue_health,
            "error_health": error_health,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global event bus instance
event_bus = EventBus()

# Decorator for event handlers
def event_handler(*event_types: Type[Event]):
    """Decorator to register event handlers."""
    def decorator(cls):
        # Create instance of handler
        handler_instance = cls()
        
        # Subscribe to event bus
        event_bus.subscribe(handler_instance)
        
        return cls
    return decorator

# Example event handlers
@event_handler(TelemetryReceived)
class TelemetryEventHandler(EventHandler):
    """Handler for telemetry events."""
    
    @property
    def handled_events(self) -> List[Type[Event]]:
        return [TelemetryReceived]
    
    async def handle(self, event: TelemetryReceived) -> None:
        """Handle telemetry received event."""
        logger = get_logger("telemetry_handler", machine_id=event.machine_id)
        
        # Update status (this was previously done inline)
        from ..thread_safe_status import status_manager
        
        success = status_manager.update_status(
            event.machine_id,
            rpm=event.rpm,
            feed_mm_min=event.feed_mm_min,
            state=event.state,
            timestamp=event.timestamp_utc
        )
        
        if success:
            logger.info("telemetry_processed", rpm=event.rpm, state=event.state)
        else:
            logger.error("telemetry_processing_failed")

@event_handler(MachineStatusChanged, AlertTriggered)
class NotificationEventHandler(EventHandler):
    """Handler for notifications and alerts."""
    
    @property
    def handled_events(self) -> List[Type[Event]]:
        return [MachineStatusChanged, AlertTriggered]
    
    async def handle(self, event: Event) -> None:
        """Handle notification events."""
        if isinstance(event, MachineStatusChanged):
            logger = get_logger("notification_handler", machine_id=event.machine_id)
            logger.info(
                "status_change_notification",
                old_state=event.old_state,
                new_state=event.new_state,
                reason=event.change_reason
            )
        elif isinstance(event, AlertTriggered):
            logger = get_logger("notification_handler", machine_id=event.machine_id)
            logger.warning(
                "alert_triggered",
                alert_type=event.alert_type,
                severity=event.severity,
                message=event.message
            )

@event_handler(SystemHealthCheck)
class HealthEventHandler(EventHandler):
    """Handler for system health events."""
    
    @property
    def handled_events(self) -> List[Type[Event]]:
        return [SystemHealthCheck]
    
    async def handle(self, event: SystemHealthCheck) -> None:
        """Handle health check events."""
        logger = get_logger("health_handler", component=event.component)
        
        if event.status == "error":
            logger.error(
                "component_error",
                component=event.component,
                metrics=event.metrics
            )
        elif event.status == "degraded":
            logger.warning(
                "component_degraded",
                component=event.component,
                metrics=event.metrics
            )
        else:
            logger.info(
                "component_healthy",
                component=event.component,
                metrics=event.metrics
            )
