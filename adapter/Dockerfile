FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir httpx==0.27.0

# Script de demo especifico para o container adapter
COPY send_fake_events.py /app/send_fake_events.py

# Variaveis de ambiente controlam o destino e a maquina de demo
# - TELEMETRY_BASE_URL (default no script: http://backend:8001)
# - TELEMETRY_MACHINE_ID (default: M80-DEMO-01)

CMD ["python", "send_fake_events.py"]
