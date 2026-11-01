"""Fixtures: BD SQLite en memoria aislada por prueba y cliente HTTP de pruebas."""
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base
from app.main import app
from app.schemas import ReservationCreate
from app.seed import seed
from app.services import notifications


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(notifications, "LOG_PATH", str(tmp_path / "notifications.log"))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    seed(session)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    app.dependency_overrides[database.get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def tomorrow():
    return date.today() + timedelta(days=1)


@pytest.fixture()
def make_data(tomorrow):
    def _make(**overrides):
        data = dict(name="Ana Torres", email="ana@example.com", phone="987654321",
                    restaurant_id=1, date=tomorrow, time=time(13, 0), party_size=2, notes="")
        data.update(overrides)
        return ReservationCreate(**data)
    return _make
