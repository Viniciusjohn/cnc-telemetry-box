"""Worker de sincronizacao stub para o CNC Telemetry Box.

Por enquanto, este processo apenas registra mensagens periodicas indicando
que o componente de sync esta ativo. Em futuras versoes, ele devera ler o
banco local (Postgres) e enviar dados resumidos para uma Telemetry Central.
"""

from __future__ import annotations

import os
import time


def main() -> None:
    central_url = os.getenv(
        "TELEMETRY_CENTRAL_URL",
        "https://central.cnc-telemetry.example.com/v1/ingest",
    )
    interval = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))

    print("[sync] CNC Telemetry Box sync worker iniciado")
    print(f"[sync] URL da Central: {central_url}")
    print(f"[sync] Intervalo: {interval} segundos")

    try:
        while True:
            # Futuramente: ler lote de eventos do banco local e enviar para a Central
            print("[sync] heartbeat - stub em execucao (nenhum dado enviado)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[sync] Encerrando sync worker (KeyboardInterrupt)")


if __name__ == "__main__":
    main()
