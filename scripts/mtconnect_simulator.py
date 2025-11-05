#!/usr/bin/env python3
"""
Simulador MTConnect Agent - Para testes locais antes de conectar ao agente real.
Simula variação realista de RPM, Feed e Execution.

Uso:
    python3 mtconnect_simulator.py --port 5000
    curl http://localhost:5000/probe
    curl http://localhost:5000/current
"""

from fastapi import FastAPI, Response
from datetime import datetime, timezone
import random
import math
import uvicorn
import argparse

app = FastAPI()

# Estado simulado
class MachineState:
    def __init__(self):
        self.base_rpm = 4000
        self.base_feed = 1200  # mm/min
        self.execution = "ACTIVE"
        self.cycle_start = datetime.now(timezone.utc)
        self.last_transition = datetime.now(timezone.utc)
    
    def update(self):
        """Simula transições de estado e variações realistas"""
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_transition).total_seconds()
        
        # Transição de estado a cada 45-90s
        if elapsed > random.uniform(45, 90):
            states = ["ACTIVE", "FEED_HOLD", "ACTIVE", "STOPPED"]
            self.execution = random.choice(states)
            self.last_transition = now
            
            # Reset RPM/Feed em stopped
            if self.execution == "STOPPED":
                self.base_rpm = 0
                self.base_feed = 0
            elif self.execution == "FEED_HOLD":
                self.base_rpm = self.base_rpm * 0.3  # Reduz mas não zera
                self.base_feed = 0
            else:  # ACTIVE
                self.base_rpm = random.uniform(3800, 5200)
                self.base_feed = random.uniform(1000, 1500)
    
    def get_rpm(self):
        """RPM com variação sinusoidal + ruído"""
        if self.execution == "STOPPED":
            return 0
        noise = random.gauss(0, 50)
        cycle = math.sin((datetime.now(timezone.utc) - self.cycle_start).total_seconds() * 0.1) * 200
        return max(0, self.base_rpm + cycle + noise)
    
    def get_feed(self):
        """Feed com variação + ruído"""
        if self.execution in ["STOPPED", "FEED_HOLD"]:
            return 0
        noise = random.gauss(0, 20)
        return max(0, self.base_feed + noise)

state = MachineState()

@app.get("/probe")
def probe():
    """Retorna estrutura do dispositivo (simplificado)"""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<MTConnectDevices>
  <Header creationTime="2025-11-05T05:10:00Z" sender="simulator" instanceId="1"/>
  <Devices>
    <Device id="cnc-sim-001" name="CNC-SIM-001">
      <DataItems>
        <DataItem id="s1" name="Sspeed" type="ROTARY_VELOCITY" category="SAMPLE" units="REVOLUTION/MINUTE"/>
        <DataItem id="f1" name="Frt" type="PATH_FEEDRATE" category="SAMPLE" units="MILLIMETER/SECOND"/>
        <DataItem id="e1" name="exec" type="EXECUTION" category="EVENT"/>
      </DataItems>
    </Device>
  </Devices>
</MTConnectDevices>"""
    return Response(content=xml, media_type="application/xml")

@app.get("/current")
def current():
    """Retorna valores atuais (XML MTConnect)"""
    state.update()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    
    rpm = state.get_rpm()
    feed_mm_min = state.get_feed()
    feed_mm_s = feed_mm_min / 60  # MTConnect padrão é mm/s
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<MTConnectStreams>
  <Header creationTime="{now}" instanceId="1"/>
  <Streams>
    <DeviceStream name="CNC-SIM-001">
      <ComponentStream component="Spindle">
        <Samples>
          <RotaryVelocity dataItemId="s1" timestamp="{now}">{rpm:.1f}</RotaryVelocity>
        </Samples>
      </ComponentStream>
      <ComponentStream component="Path">
        <Samples>
          <PathFeedrate dataItemId="f1" timestamp="{now}" units="MILLIMETER/SECOND">{feed_mm_s:.2f}</PathFeedrate>
        </Samples>
        <Events>
          <Execution dataItemId="e1" timestamp="{now}">{state.execution}</Execution>
        </Events>
      </ComponentStream>
    </DeviceStream>
  </Streams>
</MTConnectStreams>"""
    
    return Response(content=xml, media_type="application/xml")

@app.get("/sample")
def sample(from_seq: int = None, count: int = 100):
    """Retorna stream de amostras com controle de sequência (padrão MTConnect)"""
    state.update()
    now = datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    
    # Simular sequências (em produção, seria monotônico crescente do agente)
    import time
    current_seq = int(time.time() * 10) % 1000000  # Sequência simulada
    next_seq = current_seq + 1
    first_seq = max(1, current_seq - count)
    last_seq = current_seq
    
    rpm = state.get_rpm()
    feed_mm_min = state.get_feed()
    feed_mm_s = feed_mm_min / 60  # MTConnect padrão é mm/s
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<MTConnectStreams>
  <Header creationTime="{now}" instanceId="1" 
          firstSequence="{first_seq}" lastSequence="{last_seq}" 
          nextSequence="{next_seq}"/>
  <Streams>
    <DeviceStream name="CNC-SIM-001">
      <ComponentStream component="Spindle">
        <Samples>
          <RotaryVelocity dataItemId="s1" sequence="{current_seq}" timestamp="{now}">{rpm:.1f}</RotaryVelocity>
        </Samples>
      </ComponentStream>
      <ComponentStream component="Path">
        <Samples>
          <PathFeedrate dataItemId="f1" sequence="{current_seq}" timestamp="{now}" units="MILLIMETER/SECOND">{feed_mm_s:.2f}</PathFeedrate>
        </Samples>
        <Events>
          <Execution dataItemId="e1" sequence="{current_seq}" timestamp="{now}">{state.execution}</Execution>
        </Events>
      </ComponentStream>
    </DeviceStream>
  </Streams>
</MTConnectStreams>"""
    
    return Response(content=xml, media_type="application/xml")

@app.get("/health")
def health():
    return {"status": "ok", "simulator": True}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MTConnect Simulator")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print(f"🤖 MTConnect Simulator rodando em http://{args.host}:{args.port}")
    print(f"   /probe  → Estrutura do dispositivo")
    print(f"   /current → Valores atuais")
    print(f"   /health → Health check")
    
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
