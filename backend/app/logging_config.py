"""
Logging estruturado para CNC Telemetry Windows.
Configura logging com formato JSON, níveis apropriados e context para ambiente de fábrica.
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict
import json
import os
import platform

import structlog
from pythonjsonlogger import jsonlogger

# Configuração base
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")  # json ou console

# Adaptar paths para Windows
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    LOG_DIR = os.path.join(os.getenv("PROGRAMDATA", "C:\\ProgramData"), "CNC-Telemetry", "logs")
    LOG_FILE = os.path.join(LOG_DIR, "telemetry.log")
else:
    LOG_DIR = "/var/log/cnc-telemetry"
    LOG_FILE = "/var/log/cnc-telemetry/app.log"


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Adicionar campos padrão
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["service"] = "cnc-telemetry"
        log_record["version"] = os.getenv("APP_VERSION", "v1.0.0")
        log_record["environment"] = os.getenv("ENVIRONMENT", "production")
        log_record["platform"] = platform.system()
        
        # Adicionar context se disponível
        if not log_record.get("logger"):
            log_record["logger"] = record.name
            
        # Adicionar machine_id se disponível no context
        if hasattr(record, "machine_id"):
            log_record["machine_id"] = record.machine_id


def setup_logging():
    """Configura logging estruturado para toda aplicação Windows."""
    
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
    
    # Criar diretório de logs se não existir
    os.makedirs(LOG_DIR, exist_ok=True)
    
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
                "filename": LOG_FILE,
                "maxBytes": 5242880,  # 5MB (menor para Windows)
                "backupCount": 3,     # Manter 4 arquivos no total (20MB)
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "cnc-telemetry": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }
    
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


def get_log_info() -> Dict[str, Any]:
    """Retorna informações sobre configuração de logs para diagnóstico."""
    return {
        "log_directory": LOG_DIR,
        "log_file": LOG_FILE,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        "platform": platform.system(),
        "log_file_exists": os.path.exists(LOG_FILE),
        "log_file_size_mb": round(os.path.getsize(LOG_FILE) / (1024*1024), 2) if os.path.exists(LOG_FILE) else 0
    }
