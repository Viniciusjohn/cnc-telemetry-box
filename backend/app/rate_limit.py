"""
Rate limiting configuration for CNC Telemetry Box API.
Protects against flood attacks and ensures fair usage.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
import time
from typing import Dict
import asyncio

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limits configuration
RATE_LIMITS = {
    "telemetry_ingest": "100/minute",    # 100 mensagens por minuto por IP
    "status_api": "1000/hour",          # 1000 requests por hora por IP  
    "health_api": "10000/hour",         # 10k requests por hora (monitoring)
    "machine_api": "500/hour",          # 500 requests por hora por máquina
    "default": "1000/hour"              # Default para outros endpoints
}

class CustomRateLimiter:
    """Custom rate limiter with per-machine tracking."""
    
    def __init__(self):
        self._machine_counters: Dict[str, Dict] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_old_counters(self):
        """Remove contadores antigos."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            cutoff = current_time - 3600  # Remove dados de 1h atrás
            for machine_id in list(self._machine_counters.keys()):
                machine_data = self._machine_counters[machine_id]
                # Limpar timestamps antigos
                machine_data["timestamps"] = [
                    ts for ts in machine_data["timestamps"] 
                    if ts > cutoff
                ]
                # Remover máquina se não tiver timestamps recentes
                if not machine_data["timestamps"]:
                    del self._machine_counters[machine_id]
            self._last_cleanup = current_time
    
    def check_machine_rate_limit(self, machine_id: str, limit: int = 100, window: int = 60) -> bool:
        """
        Check rate limit per machine.
        
        Args:
            machine_id: ID da máquina
            limit: Número máximo de requests
            window: Janela de tempo em segundos
            
        Returns:
            True se dentro do limite, False se excedeu
        """
        current_time = time.time()
        
        # Cleanup periódico
        self._cleanup_old_counters()
        
        # Inicializar contador da máquina se não existir
        if machine_id not in self._machine_counters:
            self._machine_counters[machine_id] = {
                "timestamps": [],
                "blocked_until": 0
            }
        
        machine_data = self._machine_counters[machine_id]
        
        # Verificar se está bloqueado
        if current_time < machine_data["blocked_until"]:
            return False
        
        # Limpar timestamps antigos (fora da janela)
        cutoff = current_time - window
        machine_data["timestamps"] = [
            ts for ts in machine_data["timestamps"] 
            if ts > cutoff
        ]
        
        # Verificar limite
        if len(machine_data["timestamps"]) >= limit:
            # Bloquear por um período
            machine_data["blocked_until"] = current_time + window
            return False
        
        # Adicionar timestamp atual
        machine_data["timestamps"].append(current_time)
        return True
    
    def get_machine_stats(self, machine_id: str) -> Dict:
        """Get statistics for a machine."""
        if machine_id not in self._machine_counters:
            return {"requests_last_hour": 0, "blocked": False}
        
        machine_data = self._machine_counters[machine_id]
        current_time = time.time()
        
        # Contar requests na última hora
        cutoff = current_time - 3600
        requests_last_hour = len([
            ts for ts in machine_data["timestamps"] 
            if ts > cutoff
        ])
        
        return {
            "requests_last_hour": requests_last_hour,
            "blocked": current_time < machine_data["blocked_until"],
            "blocked_until": machine_data["blocked_until"] if machine_data["blocked_until"] > current_time else None
        }


# Global instance
machine_limiter = CustomRateLimiter()


def rate_limit_telemetry(request: Request, machine_id: str = None):
    """
    Rate limiting middleware for telemetry endpoints.
    Combines IP-based and machine-based limiting.
    """
    client_ip = get_remote_address(request)
    
    # IP-based rate limiting
    ip_limited = limiter.check("100/minute")
    if not ip_limited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for IP",
            headers={"Retry-After": "60"}
        )
    
    # Machine-based rate limiting (se machine_id fornecido)
    if machine_id:
        machine_ok = machine_limiter.check_machine_rate_limit(machine_id, limit=100, window=60)
        if not machine_ok:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for machine {machine_id}",
                headers={"Retry-After": "60"}
            )
    
    return True


# Rate limit exception handler
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    return HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "limit": exc.detail,
            "retry_after": "60"
        },
        headers={"Retry-After": "60"}
    )
