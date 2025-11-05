#!/usr/bin/env python3
"""
Adapter MTConnect → cnc-telemetry API

Implementa padrões canônicos:
- RotaryVelocity (não SpindleSpeed)
- PathFeedrate com conversão mm/s → mm/min
- Normalização de Execution → running|stopped|idle
- /sample com controle de sequência
- Idempotência no POST /ingest
"""

import httpx
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Normalização de estados MTConnect → API
EXECUTION_MAP = {
    # Estados canônicos MTConnect
    "ACTIVE": "running",
    "READY": "idle",
    "PROGRAM_COMPLETED": "idle",
    "OPTIONAL_STOP": "idle",
    "STOPPED": "stopped",
    "FEED_HOLD": "stopped",
    "INTERRUPTED": "stopped",
    "PROGRAM_STOPPED": "stopped",
    
    # Aliases comuns de adapters terceiros
    "IDLE": "idle",
    "WAITING": "idle",
    "RUNNING": "running",
    "EXECUTING": "running",
    "PAUSED": "stopped",
    "HOLD": "stopped",
}

class MTConnectAdapter:
    def __init__(
        self,
        agent_url: str,
        api_url: str,
        machine_id: str,
        poll_interval: float = 2.0
    ):
        self.agent_url = agent_url.rstrip('/')
        self.api_url = api_url.rstrip('/')
        self.machine_id = machine_id
        self.poll_interval = poll_interval
        
        self.client = httpx.AsyncClient(timeout=10.0)
        self.next_sequence: Optional[int] = None
        self.samples_sent = 0
        self.errors = 0
    
    async def discover(self) -> Dict[str, Any]:
        """Probe do agente MTConnect para descobrir DataItems"""
        try:
            response = await self.client.get(f"{self.agent_url}/probe")
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            data_items = root.findall(".//DataItem")
            
            discovered = {
                "rpm": None,
                "feed": None,
                "execution": None
            }
            
            for item in data_items:
                item_type = item.get("type", "")
                item_id = item.get("id", "")
                
                if item_type == "ROTARY_VELOCITY":
                    discovered["rpm"] = item_id
                elif item_type == "SPINDLE_SPEED":  # Fallback legacy
                    if not discovered["rpm"]:
                        discovered["rpm"] = item_id
                        logger.warning(f"Usando SpindleSpeed (deprecated) - ID: {item_id}")
                elif item_type == "PATH_FEEDRATE":
                    discovered["feed"] = item_id
                elif item_type == "EXECUTION":
                    discovered["execution"] = item_id
            
            logger.info(f"Descoberta: {discovered}")
            return discovered
            
        except Exception as e:
            logger.error(f"Erro no probe: {e}")
            return {}
    
    async def fetch_sample(self) -> Optional[ET.Element]:
        """Busca /sample com controle de sequência"""
        try:
            if self.next_sequence:
                url = f"{self.agent_url}/sample?from={self.next_sequence}&count=200"
            else:
                url = f"{self.agent_url}/sample?count=1"
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            
            # Capturar nextSequence
            header = root.find(".//Header")
            if header is not None:
                self.next_sequence = int(header.get("nextSequence", 0))
            
            return root
            
        except Exception as e:
            logger.error(f"Erro ao buscar /sample: {e}")
            self.errors += 1
            return None
    
    def parse_telemetry(self, root: ET.Element) -> Optional[Dict[str, Any]]:
        """Extrai e normaliza telemetria do XML"""
        try:
            # Priorizar RotaryVelocity sobre SpindleSpeed
            rpm_elem = root.find(".//RotaryVelocity")
            if rpm_elem is None:
                rpm_elem = root.find(".//SpindleSpeed")
                if rpm_elem is not None:
                    logger.warning("Usando SpindleSpeed (deprecated)")
            
            rpm = float(rpm_elem.text) if rpm_elem is not None else 0.0
            
            # PathFeedrate
            feed_elem = root.find(".//PathFeedrate")
            if feed_elem is not None:
                feed_value = float(feed_elem.text)
                units = feed_elem.get("units", "")
                
                # Converter mm/s → mm/min se necessário
                if "SECOND" in units:
                    feed_mm_min = feed_value * 60
                else:
                    feed_mm_min = feed_value
            else:
                feed_mm_min = 0.0
            
            # Execution
            exec_elem = root.find(".//Execution")
            exec_value = exec_elem.text if exec_elem is not None else "READY"
            
            # Normalizar estado
            state = EXECUTION_MAP.get(exec_value)
            if state is None:
                logger.warning(f"Estado desconhecido: {exec_value} (mapeado para idle)")
                state = "idle"
            
            # Timestamp do XML ou UTC atual
            timestamp_elem = rpm_elem if rpm_elem is not None else exec_elem
            timestamp_str = timestamp_elem.get("timestamp") if timestamp_elem is not None else None
            
            if timestamp_str:
                timestamp = timestamp_str
            else:
                timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
            
            # Validar faixas
            if rpm > 30000:
                logger.warning(f"RPM outlier: {rpm} (ignorado)")
                return None
            
            if feed_mm_min > 10000:
                logger.warning(f"Feed outlier: {feed_mm_min} (ignorado)")
                return None
            
            return {
                "machine_id": self.machine_id,
                "timestamp": timestamp,
                "rpm": round(rpm, 1),
                "feed_mm_min": round(feed_mm_min, 2),
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Erro ao parsear telemetria: {e}")
            self.errors += 1
            return None
    
    async def ingest(self, payload: Dict[str, Any]) -> bool:
        """POST /v1/telemetry/ingest com idempotência"""
        try:
            response = await self.client.post(
                f"{self.api_url}/v1/telemetry/ingest",
                json=payload,
                headers={
                    "X-Request-Id": f"{self.machine_id}-{payload['timestamp']}",
                    "X-Contract-Fingerprint": "010191590cf1"
                }
            )
            
            if response.status_code in (200, 201):
                self.samples_sent += 1
                return True
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                self.errors += 1
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar /ingest: {e}")
            self.errors += 1
            return False
    
    async def run(self, duration_minutes: Optional[int] = None):
        """Loop principal do adapter"""
        logger.info(f"🚀 Adapter iniciado: {self.agent_url} → {self.api_url}")
        logger.info(f"   Machine ID: {self.machine_id}")
        logger.info(f"   Polling: {self.poll_interval}s")
        
        # Descoberta inicial
        await self.discover()
        
        start_time = datetime.now(timezone.utc)
        end_time = None
        if duration_minutes:
            from datetime import timedelta
            end_time = start_time + timedelta(minutes=duration_minutes)
        
        try:
            while True:
                if end_time and datetime.now(timezone.utc) >= end_time:
                    break
                
                # Fetch sample
                root = await self.fetch_sample()
                if root is None:
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Parse
                payload = self.parse_telemetry(root)
                if payload is None:
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Ingest
                success = await self.ingest(payload)
                
                if success:
                    logger.info(
                        f"✅ #{self.samples_sent} | "
                        f"RPM={payload['rpm']} "
                        f"Feed={payload['feed_mm_min']} "
                        f"State={payload['state']} "
                        f"Seq={self.next_sequence}"
                    )
                
                await asyncio.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Interrompido pelo usuário")
        finally:
            await self.client.aclose()
            
            # Relatório final
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            expected = int(elapsed / self.poll_interval)
            loss_pct = ((expected - self.samples_sent) * 100 / expected) if expected > 0 else 0
            
            logger.info("")
            logger.info(f"📊 Relatório Final")
            logger.info(f"   Duração: {elapsed:.0f}s")
            logger.info(f"   Amostras enviadas: {self.samples_sent}")
            logger.info(f"   Erros: {self.errors}")
            logger.info(f"   Perda: {loss_pct:.2f}%")


async def main():
    import os
    
    adapter = MTConnectAdapter(
        agent_url=os.getenv("AGENT_URL", "http://localhost:5000"),
        api_url=os.getenv("API_URL", "http://localhost:8001"),
        machine_id=os.getenv("MACHINE_ID", "ABR-850"),
        poll_interval=float(os.getenv("POLL_INTERVAL", "2.0"))
    )
    
    duration = os.getenv("DURATION_MIN")
    duration_min = int(duration) if duration else None
    
    await adapter.run(duration_minutes=duration_min)


if __name__ == "__main__":
    asyncio.run(main())
