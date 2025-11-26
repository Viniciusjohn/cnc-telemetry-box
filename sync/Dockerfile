FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY sync_worker.py /app/sync_worker.py

CMD ["python", "sync_worker.py"]
