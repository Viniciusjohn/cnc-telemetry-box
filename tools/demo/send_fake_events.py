"""Modo demo para o CNC Telemetry.

Envia eventos artificiais para demonstrar o painel sem conexão com a CNC.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import httpx

BASE_URL = os.getenv("TELEMETRY_BASE_URL", "http://localhost:8001")
MACHINE_ID = os.getenv("TELEMETRY_MACHINE_ID", "DEMO_MACHINE")
EVENTS = [
    ("IDLE", "DEMO_IDLE"),
    ("RUNNING", "DEMO_RUN_001"),
    ("RUNNING", "DEMO_RUN_001"),
    ("ALARM", "DEMO_ALARM_001"),
]


def send_payload(state: str, program: str) -> None:
    payload = {
        "machine_id": MACHINE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rpm": 2000 if state == "RUNNING" else 0,
        "feed_mm_min": 150 if state == "RUNNING" else 0,
        "state": "running" if state == "RUNNING" else ("idle" if state == "IDLE" else "stopped"),
    }

    url = f"{BASE_URL}/v1/telemetry/ingest"
    with httpx.Client(timeout=5) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    print(f"[DEMO] Enviado {state} ({program}) -> {resp.status_code}")


def main() -> None:
    print("=== CNC Telemetry Demo Mode ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Machine ID: {MACHINE_ID}")
    for idx, (state, program) in enumerate(EVENTS, start=1):
        send_payload(state, program)
        if idx < len(EVENTS):
            time.sleep(2)
    print("=== Demo concluída ===")


if __name__ == "__main__":
    main()
