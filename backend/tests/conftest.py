import pytest
import sys
import os

# Add parent directory to path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.routers import status as status_router
from backend.main import app as fastapi_app

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Criar tabelas ORM e auxiliares necessárias para os endpoints de histórico
Base.metadata.create_all(bind=engine)
AUX_TABLES = (
    """
    CREATE TABLE IF NOT EXISTS telemetry_5m (
        bucket TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        rpm_avg FLOAT,
        rpm_max FLOAT,
        rpm_min FLOAT,
        feed_avg FLOAT,
        feed_max FLOAT,
        feed_min FLOAT,
        state_mode TEXT,
        sample_count INTEGER,
        uptime_ratio FLOAT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS telemetry_1h (
        bucket TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        rpm_avg FLOAT,
        rpm_max FLOAT,
        feed_avg FLOAT,
        sample_count INTEGER,
        uptime_ratio FLOAT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS telemetry_1d (
        date TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        rpm_avg FLOAT,
        rpm_max FLOAT,
        feed_avg FLOAT,
        sample_count INTEGER,
        availability FLOAT
    )
    """,
)
with engine.begin() as conn:
    for ddl in AUX_TABLES:
        conn.exec_driver_sql(ddl)


@pytest.fixture(scope="session")
def app():
    """FastAPI app com dependências apontando para o SQLite em memória."""

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_db():
    """Limpa tabelas entre testes para evitar dependências.

    [ASSUNCAO]: uso de DELETE simples é suficiente porque SQLite é isolado.
    """

    session = TestingSessionLocal()
    try:
        for table in (
            "telemetry_events",
            "telemetry",
            "telemetry_5m",
            "telemetry_1h",
            "telemetry_1d",
            "oee_daily",
        ):
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
    finally:
        session.close()
    from backend.app.routers import status
    status.LAST_STATUS.clear()
    yield


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
