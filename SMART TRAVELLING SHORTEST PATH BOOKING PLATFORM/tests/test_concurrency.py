"""Real concurrent workload tests; PostgreSQL uses independent DB connections."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from railora.db import Database
from railora.models import Booking, SeatAssignment
from railora.services import RailService


def test_simultaneous_bookings_never_oversell(services, db, request_factory):
    _, rail = services
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: rail.create_booking(2, request_factory(key=f"parallel-{i:08d}")), range(18)))
    confirmed = [r for r in results if r["status"] == "confirmed"]
    assert len(confirmed) == 6
    assert len([r for r in results if r["status"] == "waitlisted"]) == 12
    seats = [s for r in confirmed for s in r["seat_numbers"]]
    assert len(seats) == len(set(seats)) == 6
    with db.read() as s:
        assert s.scalar(select(func.count()).select_from(SeatAssignment)) == 6


def test_simultaneous_retries_are_idempotent(services, db, request_factory):
    _, rail = services
    request = request_factory(key="identical-request", size=2)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: rail.create_booking(2, request), range(12)))
    assert len({r["pnr"] for r in results}) == 1
    with db.read() as s:
        assert s.scalar(select(func.count()).select_from(Booking)) == 1
        assert s.scalar(select(func.count()).select_from(SeatAssignment)) == 2


@pytest.mark.postgres
def test_postgresql_locks_work_across_service_instances(services, db, request_factory):
    if db.is_sqlite:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL *_test database.")
    second_db = Database(str(db.engine.url.render_as_string(hide_password=False)))
    first = services[1]
    second = RailService(second_db)
    try:

        def attempt(i):
            service = first if i % 2 == 0 else second
            return service.create_booking(2, request_factory(key=f"cross-instance-{i:08d}"))

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(attempt, range(20)))
        confirmed = [r for r in results if r["status"] == "confirmed"]
        assert len(confirmed) == 6
        assert len({r["seat_numbers"][0] for r in confirmed}) == 6
    finally:
        second_db.engine.dispose()
