"""State-machine, transaction, authorisation and engineering integration tests."""

from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from railora.config import today, utcnow
from railora.db import Repository
from railora.models import AuditEvent, Booking, LoginSession, SeatAssignment, Train, User
from railora.schemas import RegisterInput, TrainInput
from railora.services import DomainError, RailService
from railora.tickets import ticket_pdf


def test_login_register_sessions_and_generic_repository(services, db):
    auth, rail = services
    token, user = auth.login(" USER@example.com ", "Railora@123")
    assert user["role"] == "user"
    assert auth.current_user(token)["id"] == 2
    auth.logout(token)
    with pytest.raises(DomainError):
        auth.current_user(token)
    for token in [None, "bad-token"]:
        with pytest.raises(DomainError):
            auth.current_user(token)
    for email in ["user@example.com", "missing@example.com"]:
        with pytest.raises(DomainError):
            auth.login(email, "wrongpassword")
    token, user = auth.register(RegisterInput(name="New Traveler", email="new@example.com", password="NewPass123"))
    assert user["role"] == "user"
    assert auth.current_user(token)["email"] == "new@example.com"
    with pytest.raises(DomainError):
        auth.register(RegisterInput(name="New Traveler", email="new@example.com", password="NewPass123"))
    with db.transaction() as s:
        for login in s.scalars(select(LoginSession)):
            login.expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(DomainError):
        auth.current_user(token)
    with db.read() as s:
        assert len(Repository(s, User).all()) == 4


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "X", "email": "wrong", "password": "12345678"},
        {"name": "Okay", "email": "ok@x.com", "password": "short"},
    ],
)
def test_registration_validates_input(payload):
    with pytest.raises(ValidationError):
        RegisterInput(**payload)


def test_booking_is_atomic_idempotent_and_pdf_is_generated(services, request_factory, db):
    _, rail = services
    request = request_factory(size=2)
    booking = rail.create_booking(2, request)
    retry = rail.create_booking(2, request)
    assert booking["pnr"] == retry["pnr"]
    assert booking["status"] == "confirmed"
    assert booking["seat_numbers"] == [1, 2]
    assert booking["fare"] == 1040
    assert booking["payment_reference"].startswith("DEMO-")
    assert rail.seat_map(1, request.journey_date, "CC")[0]["taken"]
    assert len(rail.events(2)) == 1
    assert ticket_pdf(booking).startswith(b"%PDF-")
    with db.read() as s:
        assert s.scalar(select(func.count()).select_from(Booking)) == 1
    with pytest.raises(DomainError):
        rail.create_booking(2, request.model_copy(update={"mode": "reserve"}))


def test_full_train_waitlist_cancel_and_promotion(services, request_factory):
    _, rail = services
    full = rail.create_booking(2, request_factory(size=6, key="full-request"))
    waiting = rail.create_booking(3, request_factory(key="wait-request"))
    assert waiting["status"] == "waitlisted"
    assert not waiting["seats"]
    with pytest.raises(DomainError):
        rail.create_booking(3, request_factory(key="no-waitlist", allow_waitlist=False))
    rail.cancel(2, full["pnr"])
    promoted = rail.booking(3, waiting["pnr"])
    assert promoted["status"] == "reserved"
    assert promoted["expires_at"]
    assert promoted["seat_numbers"] == [1]
    assert any(e["kind"] == "promoted" for e in rail.events(3))
    assert rail.confirm(3, promoted["pnr"])["status"] == "confirmed"
    assert rail.confirm(3, promoted["pnr"])["status"] == "confirmed"
    assert rail.cancel(2, full["pnr"])["status"] == "cancelled"


def test_fifo_groups_do_not_jump_queue(services, request_factory):
    _, rail = services
    booked = [rail.create_booking(2, request_factory(key=f"seat-{i:08d}")) for i in range(6)]
    head = rail.create_booking(3, request_factory(key="group-head", size=4))
    tail = rail.create_booking(3, request_factory(key="group-tail", size=2))
    for b in booked[:2]:
        rail.cancel(2, b["pnr"])
    assert rail.booking(3, head["pnr"])["status"] == "waitlisted"
    assert rail.booking(3, tail["pnr"])["status"] == "waitlisted"
    newcomer = rail.create_booking(2, request_factory(key="newcomer-01"))
    assert newcomer["status"] == "waitlisted"
    for b in booked[2:4]:
        rail.cancel(2, b["pnr"])
    assert rail.booking(3, head["pnr"])["status"] == "reserved"
    assert rail.booking(3, tail["pnr"])["status"] == "waitlisted"
    rail.cancel(3, head["pnr"])
    assert rail.booking(3, tail["pnr"])["status"] == "reserved"
    assert rail.booking(2, newcomer["pnr"])["status"] == "reserved"


def test_expiry_releases_seats_and_promotes_waitlist(services, request_factory, db):
    _, rail = services
    hold = rail.create_booking(2, request_factory(key="hold-request", size=6, mode="reserve"))
    waiting = rail.create_booking(3, request_factory(key="wait-request"))
    with db.transaction() as s:
        s.get(Booking, hold["pnr"]).expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(DomainError):
        rail.confirm(2, hold["pnr"])
    assert rail.expire_holds() == 1
    assert rail.booking(2, hold["pnr"])["status"] == "expired"
    assert not rail.booking(2, hold["pnr"])["seats"]
    assert rail.booking(3, waiting["pnr"])["status"] == "reserved"
    assert rail.expire_holds() == 0
    assert rail.cancel(2, hold["pnr"])["status"] == "expired"


def test_ticket_ownership_and_admin_only_controls(services, request_factory):
    _, rail = services
    booking = rail.create_booking(2, request_factory())
    for operation in [rail.booking, rail.cancel, rail.confirm]:
        with pytest.raises(DomainError) as error:
            operation(3, booking["pnr"])
        assert error.value.status_code == 403
    assert rail.booking(1, booking["pnr"])["pnr"] == booking["pnr"]
    with pytest.raises(DomainError):
        rail.admin_stats(2)
    with pytest.raises(DomainError):
        rail.events(2, admin=True)
    with pytest.raises(DomainError):
        rail.all_trains(2)
    assert rail.cancel(1, booking["pnr"])["status"] == "cancelled"


def test_date_user_train_and_sort_validation(services, request_factory):
    _, rail = services
    for request in [
        request_factory().model_copy(update={"journey_date": today() - timedelta(days=1)}),
        request_factory().model_copy(update={"journey_date": today() + timedelta(days=61)}),
        request_factory(train=999),
    ]:
        with pytest.raises(DomainError):
            rail.create_booking(2, request)
    with pytest.raises(DomainError):
        rail.create_booking(999, request_factory())
    with pytest.raises(DomainError):
        rail.search(travel_class="BAD")
    with pytest.raises(DomainError):
        rail.search(sort="BAD")
    with pytest.raises(DomainError):
        rail.booking(2, "missing")
    with pytest.raises(DomainError):
        rail.cancel(2, "missing")
    with pytest.raises(DomainError):
        rail.seat_map(999, today(), "CC")
    with pytest.raises(DomainError):
        rail.seat_map(1, today(), "BAD")
    assert len(rail.stations()) == 4
    assert len(rail.search()) == 2
    assert [t["base_fare"] for t in rail.search(sort="fare")] == [500, 750]
    assert [t["duration"] for t in rail.search(sort="duration")] == [120, 240]


def test_departed_today_and_past_cancellation(services, request_factory, db):
    _, rail = services
    with db.transaction() as s:
        s.get(Train, 1).departure = "00:00"
    with pytest.raises(DomainError):
        rail.create_booking(2, request_factory().model_copy(update={"journey_date": today()}))
    booking = rail.create_booking(2, request_factory())
    with db.transaction() as s:
        s.get(Booking, booking["pnr"]).journey_date = today() - timedelta(days=1)
    with pytest.raises(DomainError):
        rail.cancel(2, booking["pnr"])


def train_payload(number="22222", **kwargs):
    values = {
        "number": number,
        "name": "New Test Express",
        "origin": "NDLS",
        "destination": "JP",
        "departure": "08:00",
        "arrival": "10:00",
        "duration": 120,
        "base_fare": 600,
        "capacity": 12,
    }
    values.update(kwargs)
    return TrainInput(**values)


def test_admin_add_pause_resume_stats_and_csv(services, request_factory, db):
    _, rail = services
    with pytest.raises(DomainError):
        rail.add_train(2, train_payload())
    with pytest.raises(DomainError):
        rail.add_train(1, train_payload(origin="UNKNOWN"))
    added = rail.add_train(1, train_payload())
    assert added["number"] == "22222"
    with pytest.raises(DomainError):
        rail.add_train(1, train_payload())
    assert rail.toggle_train(1, added["id"]) is False
    assert not [t for t in rail.search() if t["id"] == added["id"]]
    with pytest.raises(DomainError):
        rail.create_booking(2, request_factory(train=added["id"]))
    assert rail.toggle_train(1, added["id"]) is True
    with pytest.raises(DomainError):
        rail.toggle_train(2, added["id"])
    with pytest.raises(DomainError):
        rail.toggle_train(1, 999)
    with pytest.raises(ValidationError):
        train_payload(destination="NDLS")
    with db.transaction() as s:
        s.get(User, 2).name = '=HYPERLINK("evil")'
    booking = rail.create_booking(2, request_factory())
    stats = rail.admin_stats(1)
    assert stats["total_bookings"] == 1
    assert stats["active_trains"] == 3
    assert stats["revenue"] == 520
    assert len(stats["daily_bookings"]) == 7
    assert "'=HYPERLINK" in rail.export_bookings_csv(1).replace('""', '"')
    assert len(rail.graph()["NDLS"]) == 3
    assert rail.booking(2, booking["pnr"])["passenger_name"].startswith("=")


def test_payment_exception_rolls_back_entire_reservation(services, db, request_factory):
    class BrokenPayment:
        def pay(self, amount, reference):
            raise RuntimeError("Provider failed")

    rail = RailService(db, payment=BrokenPayment())
    with pytest.raises(RuntimeError):
        rail.create_booking(2, request_factory())
    with db.read() as s:
        for model in [Booking, SeatAssignment, AuditEvent]:
            assert s.scalar(select(func.count()).select_from(model)) == 0


def test_database_guard_prevents_duplicate_seat(services, request_factory, db):
    _, rail = services
    b = rail.create_booking(2, request_factory())
    with pytest.raises(IntegrityError), db.transaction() as s:
        s.add(
            SeatAssignment(
                train_id=1,
                journey_date=today() + timedelta(days=1),
                travel_class="CC",
                seat_number=1,
                booking_pnr=b["pnr"],
            )
        )
    assert len(rail.booking(2, b["pnr"])["seats"]) == 1


@pytest.mark.parametrize("bad_value", ["passenger_name", "registered_name", "train_name", "duration"])
def test_schema_rejects_blank_names_and_inconsistent_schedule(bad_value):
    from railora.schemas import PassengerInput

    with pytest.raises(ValidationError):
        if bad_value == "passenger_name":
            PassengerInput(name="  ", age=20)
        elif bad_value == "registered_name":
            RegisterInput(name="  ", email="okay@example.com", password="LongPass123")
        elif bad_value == "train_name":
            train_payload(name="   ")
        else:
            train_payload(duration=180)


def test_admin_charts_bucket_utc_into_indian_calendar_day(services, db, request_factory):
    from datetime import datetime, time

    from railora.config import local_day

    _, rail = services
    booking = rail.create_booking(2, request_factory())
    late_utc = datetime.combine(today() - timedelta(days=1), time(20, 0))
    assert local_day(late_utc.isoformat()) == today().isoformat()
    with db.transaction() as session:
        session.get(Booking, booking["pnr"]).created_at = late_utc
    stats = rail.admin_stats(1)
    assert stats["daily_bookings"][-1] == 1
    assert stats["daily_revenue"][-1] == booking["fare"]
