FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Dependencias do backend
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o codigo do backend como pacote `backend`
COPY . /app/backend

EXPOSE 8001

# Em modo container, executa diretamente o app FastAPI via uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
