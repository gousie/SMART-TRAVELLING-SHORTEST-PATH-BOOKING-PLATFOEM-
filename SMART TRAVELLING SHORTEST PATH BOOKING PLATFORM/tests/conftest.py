"""Isolated data: NEVER point TEST_DATABASE_URL at a non-test database."""

import os
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from railora.api import domain_error_handler, make_router
from railora.config import today
from railora.db import Database
from railora.models import Base, Station, Train, User
from railora.schemas import BookingInput, PassengerInput
from railora.services import AuthService, DomainError, RailService


@pytest.fixture
def db(tmp_path):
    url = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    if not url.startswith("sqlite"):
        assert (make_url(url).database or "").endswith("_test"), "Refusing to reset a non-test PostgreSQL database!"
    database = Database(url)
    Base.metadata.drop_all(database.engine)
    database.create_schema()
    yield database
    Base.metadata.drop_all(database.engine)
    database.engine.dispose()


@pytest.fixture
def services(db):
    auth = AuthService(db)
    with db.transaction() as session:
        password = auth.hasher.hash("Railora@123")
        session.add_all(
            [
                User(name="Test Admin", email="admin@example.com", role="admin", password_hash=password),
                User(name="Test Traveler", email="user@example.com", role="user", password_hash=password),
                User(name="Other Traveler", email="other@example.com", role="user", password_hash=password),
            ]
        )
        for code in ["NDLS", "AGC", "JP", "BZA"]:
            session.add(Station(code=code, name=code, city=code, latitude=20.0, longitude=80.0))
        session.flush()
        session.add_all(
            [
                Train(
                    number="12002",
                    name="Test Express",
                    origin="NDLS",
                    destination="AGC",
                    departure="06:00",
                    arrival="08:00",
                    duration=120,
                    base_fare=500,
                    capacity=6,
                ),
                Train(
                    number="12014",
                    name="Second Express",
                    origin="NDLS",
                    destination="JP",
                    departure="12:00",
                    arrival="16:00",
                    duration=240,
                    base_fare=750,
                    capacity=36,
                ),
            ]
        )
    return auth, RailService(db)


@pytest.fixture
def request_factory():
    def make(key="request-0001", size=1, mode="book", train=1, **kwargs):
        return BookingInput(
            train_id=train,
            journey_date=today() + timedelta(days=1),
            travel_class="CC",
            passengers=[PassengerInput(name=f"Traveler {i}", age=28, gender="Other") for i in range(size)],
            mode=mode,
            idempotency_key=key,
            **kwargs,
        )

    return make


@pytest.fixture
def client(services):
    auth, rail = services
    application = FastAPI()
    application.include_router(make_router(auth, rail))
    application.add_exception_handler(DomainError, domain_error_handler)
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def user_header(client):
    token = client.post("/api/login", json={"email": "user@example.com", "password": "Railora@123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_header(client):
    token = client.post("/api/login", json={"email": "admin@example.com", "password": "Railora@123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}
