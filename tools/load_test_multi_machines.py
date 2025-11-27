#!/usr/bin/env python3
"""
Stress test para CNC Telemetry Box - Multi-máquinas
Simula N máquinas enviando telemetria em paralelo via HTTP POST
"""

import argparse
import asyncio
import random
import time
import httpx
from datetime import datetime, timezone

# Máquinas simuladas (até 50 para testes)
MACHINES = [f"M80-BOX-{i:02d}" for i in range(1, 51)]

# Estados possíveis da máquina
STATES = ["running", "stopped", "idle"]

async def send_telemetry_loop(client: httpx.AsyncClient, base_url: str, machine_id: str, interval: float) -> None:
    """Loop infinito enviando telemetria de uma máquina"""
    print(f"[{machine_id}] Iniciando envio a cada {interval}s")
    
    while True:
        # Gerar payload realista
        payload = {
            "machine_id": machine_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "rpm": random.randint(800, 3000) if random.random() > 0.2 else 0,
            "feed_mm_min": random.randint(300, 1500) if random.random() > 0.2 else 0,
            "state": random.choice(STATES)
        }
        
        try:
            # Enviar para endpoint de ingest
            resp = await client.post(f"{base_url}/v1/telemetry/ingest", json=payload, timeout=5)
            if resp.status_code not in [200, 201]:
                print(f"[{machine_id}] ERRO HTTP {resp.status_code}: {resp.text[:100]}")
            
            # Opcional: print a cada 10 mensagens para não poluir
            if random.random() < 0.1:  # 10% das mensagens
                print(f"[{machine_id}] OK - RPM:{payload['rpm']} State:{payload['state']}")
                
        except httpx.TimeoutException:
            print(f"[{machine_id}] TIMEOUT")
        except httpx.ConnectError:
            print(f"[{machine_id}] CONEXÃO RECUSADA")
        except Exception as e:
            print(f"[{machine_id}] ERRO: {str(e)[:50]}")
        
        await asyncio.sleep(interval)

async def main():
    parser = argparse.ArgumentParser(description="Stress test CNC Telemetry Box")
    parser.add_argument("--api-url", default="http://127.0.0.1:8001", help="URL da API do Box")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalo entre envios (segundos)")
    parser.add_argument("--machines", type=int, default=5, help="Número de máquinas simuladas")
    parser.add_argument("--duration", type=int, help="Duração do teste em segundos (opcional)")
    parser.add_argument("--verbose", action="store_true", help="Output detalhado")
    
    args = parser.parse_args()
    
    if args.machines > len(MACHINES):
        print(f"ERRO: Máximo de {len(MACHINES)} máquinas suportadas")
        return
    
    machines = MACHINES[:args.machines]
    print(f"=== CNC Telemetry Box - Stress Test ===")
    print(f"API: {args.api_url}")
    print(f"Máquinas: {len(machines)}")
    print(f"Intervalo: {args.interval}s")
    print(f"Duração: {'Ilimitado' if not args.duration else f'{args.duration}s'}")
    print(f"Máquinas: {', '.join(machines)}")
    print("=" * 50)
    
    # Testar conexão inicial
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{args.api_url}/healthz")
            if resp.status_code != 200:
                print(f"ERRO: Health check falhou: {resp.status_code}")
                return
            print("✅ Health check OK")
    except Exception as e:
        print(f"ERRO: Não conectou à API: {e}")
        return
    
    # Iniciar loops de telemetria
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [
            asyncio.create_task(send_telemetry_loop(client, args.api_url, mid, args.interval))
            for mid in machines
        ]
        
        if args.duration:
            # Aguardar duração específica
            await asyncio.sleep(args.duration)
            # Cancelar todas as tasks
            for task in tasks:
                task.cancel()
            print(f"\n=== Teste concluído após {args.duration}s ===")
        else:
            # Rodar indefinidamente
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                print("\n=== Teste interrompido pelo usuário ===")
                for task in tasks:
                    task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
