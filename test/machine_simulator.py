#!/usr/bin/env python3
"""
Simulador de Máquinas CNC para Teste de Escala do CNC Telemetry Box
Gera dados realistas de múltiplas máquinas enviando telemetria simultaneamente
"""

import asyncio
import aiohttp
import random
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse
from dataclasses import dataclass

# Configuração logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MachineConfig:
    """Configuração de uma máquina CNC simulada"""
    machine_id: str
    name: str
    base_rpm: int
    max_rpm: int
    base_feed: float
    max_feed: float
    error_rate: float = 0.02  # 2% chance de erro
    
class CNCMachineSimulator:
    """Simulador de máquina CNC individual"""
    
    def __init__(self, config: MachineConfig, api_url: str):
        self.config = config
        self.api_url = api_url
        self.current_state = "IDLE"
        self.current_rpm = 0
        self.current_feed = 0.0
        self.last_event_time = datetime.now()
        self.total_events = 0
        self.errors_count = 0
        
    def _generate_realistic_telemetry(self) -> Dict[str, Any]:
        """Gera dados de telemetria realistas baseados no estado atual"""
        
        # Transições de estado realistas
        state_transitions = {
            "IDLE": {"ACTIVE": 0.3, "STOPPED": 0.05, "IDLE": 0.65},
            "ACTIVE": {"PAUSED": 0.1, "STOPPED": 0.05, "IDLE": 0.15, "ACTIVE": 0.7},
            "PAUSED": {"ACTIVE": 0.4, "STOPPED": 0.1, "IDLE": 0.2, "PAUSED": 0.3},
            "STOPPED": {"IDLE": 0.6, "ACTIVE": 0.3, "STOPPED": 0.1}
        }
        
        # Escolher próximo estado
        states = list(state_transitions[self.current_state].keys())
        probabilities = list(state_transitions[self.current_state].values())
        self.current_state = random.choices(states, probabilities)[0]
        
        # Gerar RPM e feed baseados no estado
        if self.current_state == "ACTIVE":
            # Operação normal - variação realista
            rpm_variation = random.uniform(0.95, 1.05)
            self.current_rpm = int(self.config.base_rpm * rpm_variation)
            self.current_rpm = min(self.current_rpm, self.config.max_rpm)
            
            feed_variation = random.uniform(0.9, 1.1)
            self.current_feed = self.config.base_feed * feed_variation
            self.current_feed = min(self.current_feed, self.config.max_feed)
            
        elif self.current_state == "PAUSED":
            # Pausado - RPM reduzido
            self.current_rpm = int(self.config.base_rpm * 0.1)
            self.current_feed = 0.0
            
        elif self.current_state == "IDLE":
            # Ocioso - RPM mínimo
            self.current_rpm = random.randint(100, 500)
            self.current_feed = 0.0
            
        else:  # STOPPED
            self.current_rpm = 0
            self.current_feed = 0.0
        
        # Gerar eventos ocasionalmente
        event = None
        if random.random() < 0.05:  # 5% chance de evento
            events = [
                {"type": "ALARM", "severity": "WARNING", "message": "Tool wear detected"},
                {"type": "ALARM", "severity": "ERROR", "message": "Spindle overload"},
                {"type": "INFO", "severity": "INFO", "message": "Maintenance required"},
                {"type": "CYCLE", "severity": "INFO", "message": "Cycle completed"}
            ]
            event = random.choice(events)
            self.total_events += 1
        
        # Simular erros ocasionais
        if random.random() < self.config.error_rate:
            self.errors_count += 1
            return None  # Simular falha de envio
        
        return {
            "machine_id": self.config.machine_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "state": self.current_state,
            "rpm": self.current_rpm,
            "feed_mm_min": round(self.current_feed, 2),
            "event": event,
            "sequence": self.total_events
        }
    
    async def send_telemetry(self, session: aiohttp.ClientSession) -> bool:
        """Envia dados de telemetria para a API do Box"""
        
        telemetry = self._generate_realistic_telemetry()
        if telemetry is None:
            return False
        
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.api_url}/v1/telemetry/ingest",
                json=telemetry,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    return True, response_time
                else:
                    logger.warning(f"Machine {self.config.machine_id}: HTTP {response.status}")
                    return False, response_time
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"Machine {self.config.machine_id}: Timeout")
            return False, response_time
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Machine {self.config.machine_id}: Error {e}")
            return False, response_time

class LoadTestOrchestrator:
    """Orquestrador de teste de carga com múltiplas máquinas"""
    
    def __init__(self, api_url: str, machines: List[MachineConfig]):
        self.api_url = api_url
        self.machines = machines
        self.simulators = [CNCMachineSimulator(m, api_url) for m in machines]
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],  # Novo: coletar tempos de resposta
            "start_time": None,
            "end_time": None
        }
        self.read_stats = {
            "read_requests": 0,
            "successful_reads": 0,
            "read_response_times": []
        }
    
    async def simulate_dashboard_reads(self, session: aiohttp.ClientSession):
        """Simula leituras concorrentes do dashboard (usuários visualizando dados)"""
        
        start_time = time.time()
        
        try:
            # Usar endpoints reais do backend
            queries = [
                f"{self.api_url}/healthz",
                f"{self.api_url}/machines",
                f"{self.api_url}/machines/status"
            ]
            
            query = random.choice(queries)
            
            async with session.get(
                query,
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    return True, response_time
                else:
                    return False, response_time
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return False, response_time
    
    async def run_test(self, duration_minutes: int, interval_seconds: float = 2.0, enable_reads: bool = True):
        """Executa teste de carga por duração especificada com leituras concorrentes"""
        
        logger.info(f"Iniciando teste de carga: {len(self.machines)} máquinas por {duration_minutes} minutos")
        logger.info(f"Intervalo de envio: {interval_seconds} segundos")
        if enable_reads:
            logger.info("Simulação de leituras do dashboard: ATIVADA")
        
        self.stats["start_time"] = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + (duration_minutes * 60)
            
            while time.time() < end_time:
                # Enviar telemetria de todas as máquinas simultaneamente
                write_tasks = [
                    simulator.send_telemetry(session) 
                    for simulator in self.simulators
                ]
                
                write_results = await asyncio.gather(*write_tasks, return_exceptions=True)
                
                # Processar resultados de escrita
                for result in write_results:
                    if isinstance(result, tuple):
                        success, response_time = result
                        self.stats["total_requests"] += 1
                        self.stats["response_times"].append(response_time)
                        
                        if success:
                            self.stats["successful_requests"] += 1
                        else:
                            self.stats["failed_requests"] += 1
                    else:
                        self.stats["total_requests"] += 1
                        self.stats["failed_requests"] += 1
                
                # Simular leituras concorrentes do dashboard
                if enable_reads and random.random() < 0.3:  # 30% chance de leitura
                    read_tasks = [
                        self.simulate_dashboard_reads(session)
                        for _ in range(min(3, len(self.simulators)))  # Até 3 leituras concorrentes
                    ]
                    
                    read_results = await asyncio.gather(*read_tasks, return_exceptions=True)
                    
                    for result in read_results:
                        if isinstance(result, tuple):
                            success, response_time = result
                            self.read_stats["read_requests"] += 1
                            self.read_stats["read_response_times"].append(response_time)
                            
                            if success:
                                self.read_stats["successful_reads"] += 1
                
                # Esperar próximo intervalo
                await asyncio.sleep(interval_seconds)
        
        self.stats["end_time"] = datetime.now()
        
        # Imprimir resultados
        self.print_results()
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calcula percentiles para métricas de latência"""
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "p50": sorted_values[int(n * 0.5)],
            "p90": sorted_values[int(n * 0.9)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
            "max": max(sorted_values),
            "min": min(sorted_values),
            "avg": sum(sorted_values) / n
        }
    
    def print_results(self):
        """Imprime resultados do teste com métricas avançadas"""
        
        duration = self.stats["end_time"] - self.stats["start_time"]
        success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100 if self.stats["total_requests"] > 0 else 0
        
        write_percentiles = self.calculate_percentiles(self.stats["response_times"])
        read_percentiles = self.calculate_percentiles(self.read_stats["read_response_times"])
        
        print("\n" + "="*70)
        print("📊 RESULTADOS DO TESTE DE CARGA - MÉTRICAS AVANÇADAS")
        print("="*70)
        print(f"🏭 Máquinas simuladas: {len(self.machines)}")
        print(f"⏱️  Duração: {duration}")
        
        print("\n📤 MÉTRICAS DE ESCRITA (Telemetria):")
        print(f"   Total de requests: {self.stats['total_requests']}")
        print(f"   ✅ Requests bem-sucedidos: {self.stats['successful_requests']}")
        print(f"   ❌ Requests falhados: {self.stats['failed_requests']}")
        print(f"   📈 Taxa de sucesso: {success_rate:.2f}%")
        
        if self.stats["total_requests"] > 0:
            requests_per_second = self.stats["total_requests"] / duration.total_seconds()
            print(f"   🚀 Throughput: {requests_per_second:.2f} requests/segundo")
        
        if write_percentiles:
            print("\n⏱️  LATÊNCIA DE ESCRITA (ms):")
            print(f"   Média: {write_percentiles['avg']:.1f}")
            print(f"   P50: {write_percentiles['p50']:.1f}")
            print(f"   P90: {write_percentiles['p90']:.1f}")
            print(f"   P95: {write_percentiles['p95']:.1f}")
            print(f"   P99: {write_percentiles['p99']:.1f}")
            print(f"   Min/Max: {write_percentiles['min']:.1f}/{write_percentiles['max']:.1f}")
        
        if self.read_stats["read_requests"] > 0:
            read_success_rate = (self.read_stats["successful_reads"] / self.read_stats["read_requests"]) * 100
            print("\n📥 MÉTRICAS DE LEITURA (Dashboard):")
            print(f"   Total de leituras: {self.read_stats['read_requests']}")
            print(f"   ✅ Leituras bem-sucedidas: {self.read_stats['successful_reads']}")
            print(f"   📈 Taxa de sucesso: {read_success_rate:.2f}%")
            
            if read_percentiles:
                print("\n⏱️  LATÊNCIA DE LEITURA (ms):")
                print(f"   Média: {read_percentiles['avg']:.1f}")
                print(f"   P50: {read_percentiles['p50']:.1f}")
                print(f"   P90: {read_percentiles['p90']:.1f}")
                print(f"   P95: {read_percentiles['p95']:.1f}")
                print(f"   P99: {read_percentiles['p99']:.1f}")
        
        print("="*70)

def create_machine_configs(count: int) -> List[MachineConfig]:
    """Cria configurações para N máquinas simuladas"""
    
    machines = []
    for i in range(count):
        machine_id = f"MACHINE-{i+1:03d}"
        name = f"CNC Machine {i+1}"
        
        # Variação realista entre máquinas
        base_rpm = random.choice([1000, 1500, 2000, 2400, 3000])
        max_rpm = int(base_rpm * 1.5)
        base_feed = random.choice([100.0, 150.0, 200.0, 250.0, 300.0])
        max_feed = base_feed * 1.3
        
        machines.append(MachineConfig(
            machine_id=machine_id,
            name=name,
            base_rpm=base_rpm,
            max_rpm=max_rpm,
            base_feed=base_feed,
            max_feed=max_feed,
            error_rate=random.uniform(0.01, 0.05)  # 1-5% erro
        ))
    
    return machines

async def main():
    """Função principal com opções avançadas de teste"""
    
    parser = argparse.ArgumentParser(description='Simulador de Máquinas CNC para Teste de Escala')
    parser.add_argument('--machines', type=int, default=5, help='Número de máquinas para simular')
    parser.add_argument('--duration', type=int, default=5, help='Duração do teste em minutos')
    parser.add_argument('--interval', type=float, default=2.0, help='Intervalo entre envios (segundos)')
    parser.add_argument('--api-url', type=str, default='http://localhost:8001', help='URL da API do Box')
    parser.add_argument('--no-reads', action='store_true', help='Desabilitar simulação de leituras do dashboard')
    parser.add_argument('--soak-test', type=int, help='Executar teste de soaka (longa duração) em minutos')
    
    args = parser.parse_args()
    
    # Se for soak test, usar parâmetros diferentes
    if args.soak_test:
        duration = args.soak_test
        machines = args.machines
        enable_reads = not args.no_reads
        print(f"🔥 EXECUTANDO SOAK TEST: {machines} máquinas por {duration} minutos")
    else:
        duration = args.duration
        machines = args.machines
        enable_reads = not args.no_reads
    
    # Criar configurações das máquinas
    machines_list = create_machine_configs(machines)
    
    print(f"🏭 Criando {machines} máquinas CNC simuladas...")
    for machine in machines_list[:3]:  # Mostrar primeiras 3
        print(f"   {machine.machine_id}: {machine.base_rpm}-{machine.max_rpm} RPM")
    if machines > 3:
        print(f"   ... e mais {machines - 3} máquinas")
    
    # Executar teste
    orchestrator = LoadTestOrchestrator(args.api_url, machines_list)
    await orchestrator.run_test(duration, args.interval, enable_reads)
    
    # Retornar estatísticas para uso em scripts
    return {
        "total_requests": orchestrator.stats["total_requests"],
        "successful_requests": orchestrator.stats["successful_requests"],
        "failed_requests": orchestrator.stats["failed_requests"],
        "read_requests": orchestrator.read_stats["read_requests"],
        "successful_reads": orchestrator.read_stats["successful_reads"]
    }

if __name__ == "__main__":
    asyncio.run(main())
