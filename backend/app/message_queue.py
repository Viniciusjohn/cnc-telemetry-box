"""
Message Queue integration for asynchronous communication.
Redis-based implementation with fallback to in-memory queue.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import logging
from abc import ABC, abstractmethod

from ..logging_config import get_logger

logger = get_logger("message_queue")

class QueueType(Enum):
    """Queue types."""
    FIFO = "fifo"           # First-in-first-out
    PRIORITY = "priority"   # Priority queue
    DELAYED = "delayed"     # Delayed delivery
    DEAD_LETTER = "dlq"     # Dead letter queue

@dataclass
class Message:
    """Message for queue."""
    id: str = ""
    payload: Dict[str, Any]
    headers: Dict[str, Any] = None
    timestamp: datetime = None
    priority: int = 0
    delay_until: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.headers is None:
            self.headers = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "payload": self.payload,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "delay_until": self.delay_until.isoformat() if self.delay_until else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        msg = cls(
            id=data.get("id", str(uuid.uuid4())),
            payload=data.get("payload", {}),
            headers=data.get("headers", {}),
            priority=data.get("priority", 0),
            delay_until=datetime.fromisoformat(data["delay_until"]) if data.get("delay_until") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
        
        if "timestamp" in data:
            msg.timestamp = datetime.fromisoformat(data["timestamp"])
        
        return msg

class IMessageQueue(ABC):
    """Abstract message queue interface."""
    
    @abstractmethod
    async def enqueue(self, queue_name: str, message: Message) -> bool:
        """Add message to queue."""
        pass
    
    @abstractmethod
    async def dequeue(self, queue_name: str, timeout: float = 5.0) -> Optional[Message]:
        """Remove message from queue."""
        pass
    
    @abstractmethod
    async def peek(self, queue_name: str) -> Optional[Message]:
        """Look at next message without removing."""
        pass
    
    @abstractmethod
    async def size(self, queue_name: str) -> int:
        """Get queue size."""
        pass
    
    @abstractmethod
    async def clear(self, queue_name: str) -> int:
        """Clear queue and return number of messages removed."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        pass

class InMemoryQueue(IMessageQueue):
    """In-memory queue implementation for development/testing."""
    
    def __init__(self, max_size: int = 10000):
        self._queues: Dict[str, asyncio.PriorityQueue] = {}
        self._max_size = max_size
        self._stats = {
            "messages_enqueued": 0,
            "messages_dequeued": 0,
            "messages_failed": 0,
            "queue_count": 0
        }
        self.logger = get_logger("memory_queue")
    
    async def enqueue(self, queue_name: str, message: Message) -> bool:
        """Add message to in-memory queue."""
        try:
            if queue_name not in self._queues:
                self._queues[queue_name] = asyncio.PriorityQueue(maxsize=self._max_size)
                self._stats["queue_count"] += 1
            
            # Use negative priority for max-heap behavior
            priority = -message.priority
            
            # Check delay
            if message.delay_until and message.delay_until > datetime.now(timezone.utc):
                # Add to delayed queue (simplified - just skip for now)
                self.logger.warning("delayed_messages_not_supported", queue_name=queue_name)
                return False
            
            await self._queues[queue_name].put((priority, message.timestamp, message))
            self._stats["messages_enqueued"] += 1
            
            self.logger.debug(
                "message_enqueued",
                queue=queue_name,
                message_id=message.id,
                priority=message.priority
            )
            
            return True
            
        except asyncio.QueueFull:
            self.logger.error("queue_full", queue_name=queue_name)
            self._stats["messages_failed"] += 1
            return False
    
    async def dequeue(self, queue_name: str, timeout: float = 5.0) -> Optional[Message]:
        """Remove message from in-memory queue."""
        try:
            if queue_name not in self._queues:
                return None
            
            priority, timestamp, message = await asyncio.wait_for(
                self._queues[queue_name].get(), 
                timeout=timeout
            )
            
            self._stats["messages_dequeued"] += 1
            
            self.logger.debug(
                "message_dequeued",
                queue=queue_name,
                message_id=message.id
            )
            
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error("dequeue_error", queue_name=queue_name, error=str(e))
            self._stats["messages_failed"] += 1
            return None
    
    async def peek(self, queue_name: str) -> Optional[Message]:
        """Look at next message without removing."""
        if queue_name not in self._queues:
            return None
        
        queue = self._queues[queue_name]
        if queue.empty():
            return None
        
        # Get without removing (not directly supported by PriorityQueue)
        # This is a simplified implementation
        try:
            priority, timestamp, message = queue.get_nowait()
            # Put it back
            await queue.put((priority, timestamp, message))
            return message
        except asyncio.QueueEmpty:
            return None
    
    async def size(self, queue_name: str) -> int:
        """Get queue size."""
        if queue_name not in self._queues:
            return 0
        
        return self._queues[queue_name].qsize()
    
    async def clear(self, queue_name: str) -> int:
        """Clear queue."""
        if queue_name not in self._queues:
            return 0
        
        queue = self._queues[queue_name]
        count = queue.qsize()
        
        # Create new empty queue
        self._queues[queue_name] = asyncio.PriorityQueue(maxsize=self._max_size)
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        queue_sizes = {
            name: queue.qsize() 
            for name, queue in self._queues.items()
        }
        
        return {
            **self._stats,
            "queue_sizes": queue_sizes,
            "total_queues": len(self._queues),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

class RedisQueue(IMessageQueue):
    """Redis-based queue implementation for production."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self._stats = {
            "messages_enqueued": 0,
            "messages_dequeued": 0,
            "messages_failed": 0,
            "connection_errors": 0
        }
        self.logger = get_logger("redis_queue")
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None:
            try:
                import aioredis
                self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self.logger.info("redis_connected", url=self.redis_url)
            except Exception as e:
                self.logger.error("redis_connection_failed", error=str(e))
                self._stats["connection_errors"] += 1
                raise
        
        return self._redis
    
    async def enqueue(self, queue_name: str, message: Message) -> bool:
        """Add message to Redis queue."""
        try:
            redis = await self._get_redis()
            
            # Serialize message
            message_data = json.dumps(message.to_dict())
            
            # Add to Redis list (FIFO queue)
            await redis.lpush(queue_name, message_data)
            
            # Add to priority queue if priority > 0
            if message.priority > 0:
                priority_queue = f"{queue_name}:priority"
                await redis.zadd(priority_queue, {message_data: message.priority})
            
            self._stats["messages_enqueued"] += 1
            
            self.logger.debug(
                "message_enqueued_redis",
                queue=queue_name,
                message_id=message.id
            )
            
            return True
            
        except Exception as e:
            self.logger.error("redis_enqueue_error", queue=queue_name, error=str(e))
            self._stats["messages_failed"] += 1
            return False
    
    async def dequeue(self, queue_name: str, timeout: float = 5.0) -> Optional[Message]:
        """Remove message from Redis queue."""
        try:
            redis = await self._get_redis()
            
            # Try priority queue first
            priority_queue = f"{queue_name}:priority"
            result = await redis.zpopmax(priority_queue)
            
            if result:
                message_data = result[0][0]
            else:
                # Try regular queue
                result = await redis.brpop(queue_name, timeout=int(timeout))
                if not result:
                    return None
                message_data = result[1]
            
            # Deserialize message
            message_dict = json.loads(message_data)
            message = Message.from_dict(message_dict)
            
            self._stats["messages_dequeued"] += 1
            
            self.logger.debug(
                "message_dequeued_redis",
                queue=queue_name,
                message_id=message.id
            )
            
            return message
            
        except Exception as e:
            self.logger.error("redis_dequeue_error", queue_name=queue_name, error=str(e))
            self._stats["messages_failed"] += 1
            return None
    
    async def peek(self, queue_name: str) -> Optional[Message]:
        """Look at next message without removing."""
        try:
            redis = await self._get_redis()
            
            # Check priority queue first
            priority_queue = f"{queue_name}:priority"
            result = await redis.zrange(priority_queue, 0, 0, withscores=True)
            
            if result:
                message_data = result[0][0]
            else:
                # Check regular queue
                message_data = await redis.lindex(queue_name, 0)
                if not message_data:
                    return None
            
            # Deserialize message
            message_dict = json.loads(message_data)
            return Message.from_dict(message_dict)
            
        except Exception as e:
            self.logger.error("redis_peek_error", queue_name=queue_name, error=str(e))
            return None
    
    async def size(self, queue_name: str) -> int:
        """Get queue size."""
        try:
            redis = await self._get_redis()
            
            # Get sizes of both queues
            regular_size = await redis.llen(queue_name)
            priority_size = await redis.zcard(f"{queue_name}:priority")
            
            return regular_size + priority_size
            
        except Exception as e:
            self.logger.error("redis_size_error", queue_name=queue_name, error=str(e))
            return 0
    
    async def clear(self, queue_name: str) -> int:
        """Clear queue."""
        try:
            redis = await self._get_redis()
            
            # Clear both queues
            regular_count = await redis.llen(queue_name)
            priority_count = await redis.zcard(f"{queue_name}:priority")
            
            await redis.delete(queue_name)
            await redis.delete(f"{queue_name}:priority")
            
            return regular_count + priority_count
            
        except Exception as e:
            self.logger.error("redis_clear_error", queue_name=queue_name, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis queue statistics."""
        try:
            redis = await self._get_redis()
            
            # Get all queue keys
            queue_keys = await redis.keys("*")
            
            queue_sizes = {}
            for key in queue_keys:
                if key.endswith(":priority"):
                    queue_name = key[:-9]  # Remove ":priority"
                    size = await redis.zcard(key)
                    queue_sizes[queue_name] = queue_sizes.get(queue_name, 0) + size
                else:
                    size = await redis.llen(key)
                    queue_sizes[key] = queue_sizes.get(key, 0) + size
            
            return {
                **self._stats,
                "queue_sizes": queue_sizes,
                "total_queues": len(set([k if not k.endswith(":priority") else k[:-9] for k in queue_keys])),
                "redis_connected": self._redis is not None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("redis_stats_error", error=str(e))
            return {
                **self._stats,
                "error": str(e),
                "redis_connected": False
            }

class MessageQueueManager:
    """Message queue manager with fallback support."""
    
    def __init__(self, preferred_queue: IMessageQueue = None):
        self.preferred_queue = preferred_queue or InMemoryQueue()
        self.fallback_queue = InMemoryQueue()
        self.logger = get_logger("queue_manager")
    
    async def enqueue(self, queue_name: str, message: Message) -> bool:
        """Enqueue message with fallback."""
        try:
            success = await self.preferred_queue.enqueue(queue_name, message)
            if success:
                return True
        except Exception as e:
            self.logger.warning("preferred_queue_failed", error=str(e))
        
        # Fallback
        self.logger.info("using_fallback_queue", queue=queue_name)
        return await self.fallback_queue.enqueue(queue_name, message)
    
    async def dequeue(self, queue_name: str, timeout: float = 5.0) -> Optional[Message]:
        """Dequeue message with fallback."""
        try:
            message = await self.preferred_queue.dequeue(queue_name, timeout)
            if message:
                return message
        except Exception as e:
            self.logger.warning("preferred_queue_dequeue_failed", error=str(e))
        
        # Fallback
        return await self.fallback_queue.dequeue(queue_name, timeout)
    
    async def size(self, queue_name: str) -> int:
        """Get combined queue size."""
        try:
            preferred_size = await self.preferred_queue.size(queue_name)
            fallback_size = await self.fallback_queue.size(queue_name)
            return preferred_size + fallback_size
        except Exception as e:
            self.logger.error("size_calculation_failed", error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        try:
            preferred_stats = await self.preferred_queue.get_stats()
            fallback_stats = await self.fallback_queue.get_stats()
            
            return {
                "preferred": preferred_stats,
                "fallback": fallback_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error("stats_collection_failed", error=str(e))
            return {"error": str(e)}

# Global queue manager
queue_manager: MessageQueueManager = None

def setup_message_queue(redis_url: str = None) -> MessageQueueManager:
    """Setup message queue manager."""
    global queue_manager
    
    if redis_url:
        try:
            redis_queue = RedisQueue(redis_url)
            queue_manager = MessageQueueManager(redis_queue)
            logger.info("message_queue_setup_redis", url=redis_url)
        except Exception as e:
            logger.warning("redis_setup_failed", error=str(e))
            queue_manager = MessageQueueManager()
            logger.info("message_queue_setup_fallback")
    else:
        queue_manager = MessageQueueManager()
        logger.info("message_queue_setup_memory")
    
    return queue_manager

# Decorator for queue-based processing
async def process_queue_messages(
    queue_name: str,
    handler: Callable[[Message], Any],
    batch_size: int = 10,
    timeout: float = 5.0
):
    """Process messages from queue continuously."""
    logger = get_logger("queue_processor", queue=queue_name)
    
    while True:
        try:
            messages = []
            
            # Collect batch of messages
            for _ in range(batch_size):
                message = await queue_manager.dequeue(queue_name, timeout)
                if message:
                    messages.append(message)
                else:
                    break
            
            if not messages:
                continue
            
            # Process messages
            for message in messages:
                try:
                    await handler(message)
                    logger.debug("message_processed", message_id=message.id)
                except Exception as e:
                    logger.error("message_processing_failed", message_id=message.id, error=str(e))
                    
                    # Retry logic
                    if message.retry_count < message.max_retries:
                        message.retry_count += 1
                        await queue_manager.enqueue(queue_name, message)
                        logger.info("message_queued_for_retry", message_id=message.id, retry_count=message.retry_count)
                    else:
                        logger.error("message_max_retries_exceeded", message_id=message.id)
                        
                        # Send to dead letter queue
                        await queue_manager.enqueue(f"{queue_name}:dlq", message)
            
        except Exception as e:
            logger.error("queue_processing_error", error=str(e), exc_info=True)
            await asyncio.sleep(1)  # Prevent tight loop on errors

# Queue names for different purposes
class QueueNames:
    """Standard queue names."""
    TELEMETRY_INGEST = "telemetry:ingest"
    STATUS_UPDATES = "status:updates"
    ALERTS = "alerts"
    BACKUP_TASKS = "backup:tasks"
    NOTIFICATIONS = "notifications"
    HEALTH_CHECKS = "health:checks"
    DEAD_LETTER = "dlq"
