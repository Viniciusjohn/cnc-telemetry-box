"""
Testes para endpoints multi-máquina (MM01)
"""

import pytest
import sys
import os

# Add parent directory to path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.routers.status import LAST_STATUS, MachineStatus, update_status
from backend.main import app
from backend.app.db import get_db

client = TestClient(app)

def test_list_machines_empty():
    """Testa listagem de máquinas quando nenhuma telemetria foi enviada"""
    # Limpar store
    LAST_STATUS.clear()
    
    response = client.get("/v1/machines")
    assert response.status_code == 200
    assert response.json() == []

def test_list_machines_with_data():
    """Testa listagem de máquinas com dados"""
    # Limpar store
    LAST_STATUS.clear()
    
    # Adicionar máquinas mock
    LAST_STATUS["MACHINE-001"] = MachineStatus(
        machine_id="MACHINE-001",
        controller_family="MITSUBISHI_M8X",
        timestamp_utc="2025-01-01T10:00:00Z",
        mode="AUTOMATIC",
        execution="EXECUTING",
        rpm=3500,
        feed_rate=1200,
        spindle_load_pct=50,
        tool_id="T01",
        alarm_code=None,
        alarm_message=None,
        part_count=100,
        update_interval_ms=1000,
        source="mtconnect:sim"
    )
    
    LAST_STATUS["MACHINE-002"] = MachineStatus(
        machine_id="MACHINE-002",
        controller_family="MITSUBISHI_M8X",
        timestamp_utc="2025-01-01T10:00:00Z",
        mode="MANUAL",
        execution="READY",
        rpm=0,
        feed_rate=None,
        spindle_load_pct=None,
        tool_id=None,
        alarm_code=None,
        alarm_message=None,
        part_count=None,
        update_interval_ms=1000,
        source="mtconnect:sim"
    )
    
    response = client.get("/v1/machines")
    assert response.status_code == 200
    machines = response.json()
    assert len(machines) == 2
    assert "MACHINE-001" in machines
    assert "MACHINE-002" in machines
    # Verificar ordenação
    assert machines == ["MACHINE-001", "MACHINE-002"]

def test_machines_status_grid_empty():
    """Testa grid de status quando nenhuma telemetria foi enviada"""
    # Limpar store
    LAST_STATUS.clear()
    
    response = client.get("/v1/machines/status?view=grid")
    assert response.status_code == 200
    assert response.json() == []

def test_machines_status_grid_with_data():
    """Testa grid de status com dados"""
    # Limpar store
    LAST_STATUS.clear()
    
    # Adicionar máquinas mock
    LAST_STATUS["MACHINE-001"] = MachineStatus(
        machine_id="MACHINE-001",
        controller_family="MITSUBISHI_M8X",
        timestamp_utc="2025-01-01T10:00:00Z",
        mode="AUTOMATIC",
        execution="EXECUTING",
        rpm=3500,
        feed_rate=1200,
        spindle_load_pct=50,
        tool_id="T01",
        alarm_code=None,
        alarm_message=None,
        part_count=100,
        update_interval_ms=1000,
        source="mtconnect:sim"
    )
    
    LAST_STATUS["MACHINE-002"] = MachineStatus(
        machine_id="MACHINE-002",
        controller_family="MITSUBISHI_M8X",
        timestamp_utc="2025-01-01T10:01:00Z",
        mode="MANUAL",
        execution="READY",
        rpm=0,
        feed_rate=None,
        spindle_load_pct=None,
        tool_id=None,
        alarm_code=None,
        alarm_message=None,
        part_count=None,
        update_interval_ms=1000,
        source="mtconnect:sim"
    )
    
    response = client.get("/v1/machines/status?view=grid")
    assert response.status_code == 200
    grid = response.json()
    assert len(grid) == 2
    
    # Verificar estrutura do item
    item = grid[0]
    assert "machine_id" in item
    assert "execution" in item
    assert "mode" in item
    assert "rpm" in item
    assert "timestamp_utc" in item
    assert "source" in item
    
    # Verificar ordenação
    machine_ids = [item["machine_id"] for item in grid]
    assert machine_ids == ["MACHINE-001", "MACHINE-002"]

def test_machines_status_grid_invalid_view():
    """Testa grid de status com view inválido"""
    response = client.get("/v1/machines/status?view=invalid")
    assert response.status_code == 422  # FastAPI validation error
    assert "should match pattern" in response.json()["detail"][0]["msg"]

def test_machines_status_grid_default_view():
    """Testa grid de status sem parâmetro view (deve usar default 'grid')"""
    response = client.get("/v1/machines/status")
    assert response.status_code == 200
    # Deve funcionar mesmo sem parâmetro view

def test_ingest_updates_multi_machine_store():
    """Testa se ingestão atualiza corretamente o store multi-máquina"""
    # Limpar store
    LAST_STATUS.clear()
    
    # Ingerir telemetria para máquina 1
    response = client.post("/v1/telemetry/ingest", json={
        "machine_id": "MULTI-TEST-01",
        "timestamp": "2025-01-01T10:00:00Z",
        "rpm": 3000,
        "feed_mm_min": 1000,
        "state": "running"
    })
    assert response.status_code == 201
    
    # Ingerir telemetria para máquina 2
    response = client.post("/v1/telemetry/ingest", json={
        "machine_id": "MULTI-TEST-02",
        "timestamp": "2025-01-01T10:01:00Z",
        "rpm": 1500,
        "feed_mm_min": 500,
        "state": "stopped"
    })
    assert response.status_code == 201
    
    # Verificar que ambas as máquinas estão no store
    machines_response = client.get("/v1/machines")
    machines = machines_response.json()
    assert len(machines) == 2
    assert "MULTI-TEST-01" in machines
    assert "MULTI-TEST-02" in machines
    
    # Verificar grid status
    grid_response = client.get("/v1/machines/status?view=grid")
    grid = grid_response.json()
    assert len(grid) == 2
    
    # Encontrar status de cada máquina
    machine_01_status = next(item for item in grid if item["machine_id"] == "MULTI-TEST-01")
    machine_02_status = next(item for item in grid if item["machine_id"] == "MULTI-TEST-02")
    
    assert machine_01_status["execution"] == "EXECUTING"
    assert machine_01_status["rpm"] == 3000
    assert machine_02_status["execution"] == "STOPPED"
    assert machine_02_status["rpm"] == 1500
