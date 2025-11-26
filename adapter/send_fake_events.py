"""Modo demo para o CNC Telemetry (container adapter).

Reaproveita a mesma logica do tools/demo/send_fake_events.py, enviando
telemetria fake para o backend via HTTP. Ideal para demos do Box sem CNC real.
"""
from __future__ import annotations

import argparse
import os
import random
import time
from datetime import datetime, timezone

import httpx

EVENTS = [
    ("IDLE", "DEMO_IDLE"),
    ("RUNNING", "DEMO_RUN_001"),
    ("RUNNING", "DEMO_RUN_002"),
    ("ALARM", "DEMO_ALARM_001"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enviar eventos fake para o CNC Telemetry (adapter container)")
    parser.add_argument(
        "--api-url",
        default=os.getenv("TELEMETRY_BASE_URL", "http://backend:8001"),
        help="URL base do backend (default: $TELEMETRY_BASE_URL ou http://backend:8001)",
    )
    parser.add_argument(
        "--machine-id",
        default=os.getenv("TELEMETRY_MACHINE_ID", "M80-DEMO-01"),
        help="Identificador da maquina (apenas letras, numeros e hifen)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("TELEMETRY_INTERVAL_SECONDS", "2")),
        help="Intervalo em segundos entre eventos",
    )
    parser.add_argument(
        "--burst",
        type=int,
        default=0,
        help="Numero de eventos a enviar (0 = loop infinito)",
    )
    return parser.parse_args()


def build_payload(machine_id: str, state: str) -> dict:
    return {
        "machine_id": machine_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rpm": 2000 if state == "RUNNING" else 0,
        "feed_mm_min": 150 if state == "RUNNING" else 0,
        "state": "running" if state == "RUNNING" else ("idle" if state == "IDLE" else "stopped"),
    }


def send_payload(base_url: str, payload: dict, state: str, program: str) -> None:
    url = f"{base_url.rstrip('/')}/v1/telemetry/ingest"
    with httpx.Client(timeout=5) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    print(f"[ADAPTER DEMO] {payload['timestamp']} :: {state:<8} ({program}) -> {resp.status_code}")


def main() -> None:
    args = parse_args()
    base_url = args.api_url
    machine_id = args.machine_id

    if "_" in machine_id:
        raise SystemExit("machine_id invalido: use apenas letras, numeros e hifen (-). Ex: M80-DEMO-01")

    print("=== CNC Telemetry Demo Adapter (Container) ===")
    print(f"Base URL: {base_url}")
    print(f"Machine ID: {machine_id}")
    print("Ctrl+C para interromper.\n")

    sent = 0
    while True:
        state, program = random.choice(EVENTS)
        payload = build_payload(machine_id, state)
        send_payload(base_url, payload, state, program)
        sent += 1
        if args.burst and sent >= args.burst:
            break
        time.sleep(args.interval)

    print("=== Demo concluida ===")


if __name__ == "__main__":
    main()
