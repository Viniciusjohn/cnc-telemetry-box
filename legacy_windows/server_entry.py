"""PyInstaller entrypoint for the CNC Telemetry backend."""

from pathlib import Path
import sys
import traceback

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import backend app after ensuring the path is available
from backend.main import app  # type: ignore


def main() -> None:
    """Start FastAPI backend without autoreload (for PyInstaller build)."""

    print("Iniciando CNC Telemetry gateway (exe)...")
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            reload=False,
        )
    except Exception as exc:  # noqa: BLE001
        print("ERRO FATAL no server_entry:", exc)
        traceback.print_exc()
        input("Pressione ENTER para sair...")


if __name__ == "__main__":
    main()
