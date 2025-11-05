# Base — cnc-telemetry
- Escopo: telemetria RPM, Feed (mm/min), Running/Stopped (≥15s), Tempo de usinagem.
- TERMO-BAN: "CNC-Genius".
- Stack: FastAPI | React+Vite (TS) | Playwright.
- Invariantes HTTP: X-Contract-Fingerprint: 010191590cf1, X-Request-Id, Cache-Control: no-store, Vary: Origin, Accept-Encoding, Server-Timing.
- Modo: planejar → executar (gates F0–F4).
