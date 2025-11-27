"""
Dependency Injection container for CNC Telemetry Box.
Provides loose coupling and easier testing.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar, Callable, Optional
from dataclasses import dataclass
import inspect
from functools import wraps
import logging

from ..logging_config import get_logger

logger = get_logger("dependency_injection")

T = TypeVar('T')

class DIError(Exception):
    """Dependency injection errors."""
    pass

class ServiceLifetime:
    """Service lifetime options."""
    TRANSIENT = "transient"   # New instance every time
    SINGLETON = "singleton"   # Single instance for container
    SCOPED = "scoped"         # Single instance per scope

@dataclass
class ServiceDescriptor:
    """Service registration descriptor."""
    interface: Type
    implementation: Type
    lifetime: str
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    dependencies: Optional[Dict[str, Type]] = None

class DIContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scopes: Dict[str, Dict[Type, Any]] = {}
        self._current_scope: Optional[str] = None
        self.logger = get_logger("di_container")
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> "DIContainer":
        """Register transient service."""
        return self._register(interface, implementation, ServiceLifetime.TRANSIENT)
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> "DIContainer":
        """Register singleton service."""
        return self._register(interface, implementation, ServiceLifetime.SINGLETON)
    
    def register_scoped(self, interface: Type[T], implementation: Type[T]) -> "DIContainer":
        """Register scoped service."""
        return self._register(interface, implementation, ServiceLifetime.SCOPED)
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> "DIContainer":
        """Register service with factory function."""
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=type(None),
            lifetime=ServiceLifetime.TRANSIENT,
            factory=factory
        )
        self._services[interface] = descriptor
        self.logger.debug("factory_registered", interface=interface.__name__)
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> "DIContainer":
        """Register specific instance."""
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance
        )
        self._services[interface] = descriptor
        self._singletons[interface] = instance
        self.logger.debug("instance_registered", interface=interface.__name__)
        return self
    
    def _register(self, interface: Type[T], implementation: Type[T], lifetime: str) -> "DIContainer":
        """Internal registration method."""
        # Validate that implementation implements interface
        if not issubclass(implementation, interface):
            raise DIError(f"{implementation.__name__} does not implement {interface.__name__}")
        
        # Analyze dependencies
        dependencies = self._analyze_dependencies(implementation)
        
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=dependencies
        )
        
        self._services[interface] = descriptor
        self.logger.debug(
            "service_registered",
            interface=interface.__name__,
            implementation=implementation.__name__,
            lifetime=lifetime,
            dependencies=list(dependencies.keys()) if dependencies else []
        )
        
        return self
    
    def _analyze_dependencies(self, implementation: Type) -> Dict[str, Type]:
        """Analyze constructor dependencies."""
        try:
            signature = inspect.signature(implementation.__init__)
            dependencies = {}
            
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                
                if param.annotation != inspect.Parameter.empty:
                    dependencies[param_name] = param.annotation
            
            return dependencies
            
        except Exception as e:
            self.logger.warning("dependency_analysis_failed", implementation=implementation.__name__, error=str(e))
            return {}
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve service instance."""
        if interface not in self._services:
            raise DIError(f"Service {interface.__name__} not registered")
        
        descriptor = self._services[interface]
        
        # Check for existing instance
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if interface in self._singletons:
                return self._singletons[interface]
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if self._current_scope and self._current_scope in self._scopes:
                if interface in self._scopes[self._current_scope]:
                    return self._scopes[self._current_scope][interface]
        
        # Create new instance
        instance = self._create_instance(descriptor)
        
        # Store instance based on lifetime
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            self._singletons[interface] = instance
        elif descriptor.lifetime == ServiceLifetime.SCOPED and self._current_scope:
            if self._current_scope not in self._scopes:
                self._scopes[self._current_scope] = {}
            self._scopes[self._current_scope][interface] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance with dependencies."""
        # Use factory if available
        if descriptor.factory:
            return descriptor.factory()
        
        # Use instance if available
        if descriptor.instance:
            return descriptor.instance
        
        # Create new instance with dependency injection
        implementation = descriptor.implementation
        
        if not descriptor.dependencies:
            # No dependencies, simple instantiation
            return implementation()
        
        # Resolve dependencies
        kwargs = {}
        for dep_name, dep_type in descriptor.dependencies.items():
            kwargs[dep_name] = self.resolve(dep_type)
        
        try:
            return implementation(**kwargs)
        except Exception as e:
            self.logger.error(
                "instance_creation_failed",
                implementation=implementation.__name__,
                error=str(e),
                dependencies=list(descriptor.dependencies.keys())
            )
            raise DIError(f"Failed to create {implementation.__name__}: {e}")
    
    def create_scope(self, scope_id: str = None) -> "DIScope":
        """Create new dependency scope."""
        if scope_id is None:
            import uuid
            scope_id = str(uuid.uuid4())
        
        return DIScope(self, scope_id)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about registered services."""
        return {
            "services": {
                interface.__name__: {
                    "implementation": descriptor.implementation.__name__,
                    "lifetime": descriptor.lifetime,
                    "dependencies": list(descriptor.dependencies.keys()) if descriptor.dependencies else [],
                    "has_factory": descriptor.factory is not None,
                    "has_instance": descriptor.instance is not None
                }
                for interface, descriptor in self._services.items()
            },
            "singletons": list(self._singletons.keys()),
            "scopes": list(self._scopes.keys()),
            "current_scope": self._current_scope
        }

class DIScope:
    """Dependency injection scope context manager."""
    
    def __init__(self, container: DIContainer, scope_id: str):
        self.container = container
        self.scope_id = scope_id
        self.previous_scope = None
    
    def __enter__(self) -> "DIScope":
        self.previous_scope = self.container._current_scope
        self.container._current_scope = self.scope_id
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up scope
        if self.scope_id in self.container._scopes:
            del self.container._scopes[self.scope_id]
        
        self.container._current_scope = self.previous_scope
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve service within scope."""
        return self.container.resolve(interface)

# Global container
container = DIContainer()

# Decorator for automatic dependency injection
def injectable(interface: Type[T] = None):
    """Decorator to mark class as injectable."""
    def decorator(cls):
        # If interface not provided, use class itself
        target_interface = interface or cls
        
        # Register as transient by default
        container.register_transient(target_interface, cls)
        
        return cls
    return decorator

def inject(*dependencies: Type):
    """Decorator for automatic dependency injection in functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject dependencies
            for i, dep_type in enumerate(dependencies):
                if i >= len(args) or args[i] is None:
                    # Replace None or missing argument with resolved dependency
                    new_args = list(args)
                    while len(new_args) <= i:
                        new_args.append(None)
                    new_args[i] = container.resolve(dep_type)
                    args = tuple(new_args)
            
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Inject dependencies for async functions
            for i, dep_type in enumerate(dependencies):
                if i >= len(args) or args[i] is None:
                    new_args = list(args)
                    while len(new_args) <= i:
                        new_args.append(None)
                    new_args[i] = container.resolve(dep_type)
                    args = tuple(new_args)
            
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator

# Abstract interfaces for dependency injection
class ITelemetryService(ABC):
    """Interface for telemetry service."""
    
    @abstractmethod
    async def process_telemetry(self, machine_id: str, data: Dict[str, Any]) -> bool:
        pass

class IStatusService(ABC):
    """Interface for status service."""
    
    @abstractmethod
    async def update_status(self, machine_id: str, status: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def get_status(self, machine_id: str) -> Optional[Dict[str, Any]]:
        pass

class INotificationService(ABC):
    """Interface for notification service."""
    
    @abstractmethod
    async def send_alert(self, machine_id: str, alert: Dict[str, Any]) -> None:
        pass

class IBackupService(ABC):
    """Interface for backup service."""
    
    @abstractmethod
    async def create_backup(self) -> str:
        pass
    
    @abstractmethod
    async def restore_backup(self, backup_file: str) -> bool:
        pass

# Concrete implementations
@injectable(ITelemetryService)
class TelemetryService(ITelemetryService):
    """Concrete telemetry service implementation."""
    
    def __init__(self):
        self.logger = get_logger("telemetry_service")
    
    async def process_telemetry(self, machine_id: str, data: Dict[str, Any]) -> bool:
        """Process telemetry data."""
        try:
            self.logger.info("processing_telemetry", machine_id=machine_id)
            
            # Emit event
            from ..event_bus import event_bus, TelemetryReceived
            
            event = TelemetryReceived(
                machine_id=machine_id,
                rpm=data.get("rpm", 0.0),
                feed_mm_min=data.get("feed_mm_min", 0.0),
                state=data.get("state", "idle"),
                timestamp_utc=data.get("timestamp", "")
            )
            
            await event_bus.publish(event)
            return True
            
        except Exception as e:
            self.logger.error("telemetry_processing_failed", error=str(e), exc_info=True)
            return False

@injectable(IStatusService)
class StatusService(IStatusService):
    """Concrete status service implementation."""
    
    def __init__(self):
        from ..thread_safe_status import status_manager
        self.status_manager = status_manager
        self.logger = get_logger("status_service")
    
    async def update_status(self, machine_id: str, status: Dict[str, Any]) -> bool:
        """Update machine status."""
        try:
            success = self.status_manager.update_status(machine_id, **status)
            
            if success:
                self.logger.info("status_updated", machine_id=machine_id)
            else:
                self.logger.error("status_update_failed", machine_id=machine_id)
            
            return success
            
        except Exception as e:
            self.logger.error("status_update_error", error=str(e), exc_info=True)
            return False
    
    async def get_status(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get machine status."""
        try:
            return self.status_manager.get_status(machine_id)
        except Exception as e:
            self.logger.error("status_get_error", error=str(e), exc_info=True)
            return None

@injectable(INotificationService)
class NotificationService(INotificationService):
    """Concrete notification service implementation."""
    
    def __init__(self):
        self.logger = get_logger("notification_service")
    
    async def send_alert(self, machine_id: str, alert: Dict[str, Any]) -> None:
        """Send alert notification."""
        try:
            self.logger.warning(
                "alert_sent",
                machine_id=machine_id,
                alert_type=alert.get("type"),
                message=alert.get("message")
            )
            
            # Emit alert event
            from ..event_bus import event_bus, AlertTriggered
            
            event = AlertTriggered(
                machine_id=machine_id,
                alert_type=alert.get("type", "unknown"),
                severity=alert.get("severity", "info"),
                message=alert.get("message", ""),
                threshold_value=alert.get("threshold"),
                current_value=alert.get("current")
            )
            
            await event_bus.publish(event)
            
        except Exception as e:
            self.logger.error("alert_send_failed", error=str(e), exc_info=True)

# Setup function to register all services
def setup_dependency_injection():
    """Setup dependency injection container with all services."""
    logger = get_logger("di_setup")
    
    # Services are automatically registered via @injectable decorator
    # But we can add additional configuration here
    
    logger.info("dependency_injection_configured")
    
    # Log service info
    service_info = container.get_service_info()
    logger.debug("registered_services", services=service_info["services"])
