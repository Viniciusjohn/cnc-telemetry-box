"""
Logging estruturado para CNC Telemetry Box.
Configura logging com formato JSON, níveis apropriados e context.
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict
import json
import os

import structlog
from pythonjsonlogger import jsonlogger

# Configuração base
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # json ou console


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Adicionar campos padrão
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["service"] = "cnc-telemetry"
        log_record["version"] = os.getenv("APP_VERSION", "v1.0.0")
        log_record["environment"] = os.getenv("ENVIRONMENT", "development")
        
        # Adicionar context se disponível
        if not log_record.get("logger"):
            log_record["logger"] = record.name
            
        # Adicionar machine_id se disponível no context
        if hasattr(record, "machine_id"):
            log_record["machine_id"] = record.machine_id


def setup_logging():
    """Configura logging estruturado para toda aplicação."""
    
    # Configuração structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configuração logging padrão
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": LOG_LEVEL,
                "formatter": "json" if LOG_FORMAT == "json" else "console",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": LOG_LEVEL,
                "formatter": "json",
                "filename": "/var/log/cnc-telemetry/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": LOG_LEVEL,
                "handlers": ["console", "file"] if os.path.exists("/var/log/cnc-telemetry") else ["console"],
                "propagate": False
            },
            "cnc-telemetry": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"] if os.path.exists("/var/log/cnc-telemetry") else ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Criar diretório de logs se não existir
    os.makedirs("/var/log/cnc-telemetry", exist_ok=True)
    
    # Aplicar configuração
    logging.config.dictConfig(logging_config)
    
    # Logger estruturado principal
    return structlog.get_logger("cnc-telemetry")


# Logger global
logger = setup_logging()


class TelemetryLoggerAdapter(logging.LoggerAdapter):
    """Adapter para adicionar contexto de telemetria automaticamente."""
    
    def process(self, msg, kwargs):
        # Adicionar machine_id se disponível no context
        if hasattr(self.extra, "machine_id"):
            kwargs.setdefault("extra", {})["machine_id"] = self.extra.machine_id
        return msg, kwargs


def get_logger(name: str = "cnc-telemetry", **context) -> structlog.BoundLogger:
    """Get logger com contexto opcional."""
    logger = structlog.get_logger(name)
    if context:
        return logger.bind(**context)
    return logger


def log_function_call(func):
    """Decorator para log automático de chamadas de função."""
    def wrapper(*args, **kwargs):
        logger = get_logger("function", function=func.__name__)
        start_time = datetime.now()
        
        logger.info("function_started", args_count=len(args), kwargs_count=len(kwargs))
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info("function_completed", duration_seconds=duration)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error("function_failed", duration_seconds=duration, error=str(e), exc_info=True)
            raise
    
    return wrapper
