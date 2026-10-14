"""Application layer: OOP strategies + transactionally safe reservations.

All authorisation is enforced here as well as in the API. UI components never write
ORM entities directly. SQL transactions commit booking, seats and audit events together.
"""

import secrets
from abc import ABC, abstractmethod
from collections import Counter, deque
from datetime import date, timedelta
from hashlib import sha256
from typing import Any, Protocol

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from railora.algorithms import Edge, Graph, allocate_seats, fare_quote, merge_sort, seat_labels, timed
from railora.config import local_day, today, utcnow
from railora.db import Database, Repository
from railora.models import AuditEvent, Booking, Inventory, LoginSession, SeatAssignment, Station, Train, User
from railora.schemas import BookingInput, RegisterInput, TrainInput

CLASSES = {"CC": "AC Chair Car", "3A": "AC 3 Tier", "SL": "Sleeper"}


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message, self.status_code = message, status_code
        super().__init__(message)


class FarePolicy(ABC):
    @abstractmethod
    def quote(self, base: int, travel_class: str, passengers: int) -> dict[str, int]:
        """Return an integer-rupee fare breakdown."""


class StandardFare(FarePolicy):
    def quote(self, base: int, travel_class: str, passengers: int) -> dict[str, int]:
        return fare_quote(base, travel_class, passengers)


class PaymentGateway(Protocol):
    def pay(self, amount: int, reference: str) -> str: ...


class DemoPayment:
    """No charge, no card data. Never substitute this for a real payment provider."""

    def pay(self, amount: int, reference: str) -> str:
        return f"DEMO-{reference}"


def user_dict(user: User) -> dict[str, Any]:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


class AuthService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        self.dummy_hash = self.hasher.hash("unused-timing-protection")

    def login(self, email: str, password: str) -> tuple[str, dict[str, Any]]:
        with self.db.read() as session:
            user = session.scalar(select(User).where(User.email == email.strip().lower()))
            valid: bool
            try:
                valid = self.hasher.verify(user.password_hash if user else self.dummy_hash, password)
            except VerificationError:
                valid = False
            if not user or not valid:
                raise DomainError("Email or password is incorrect.", 401)
            profile = user_dict(user)
        return self.issue_session(profile["id"]), profile

    def issue_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        with self.db.transaction() as session:
            session.add(
                LoginSession(
                    token_hash=sha256(token.encode()).hexdigest(),
                    user_id=user_id,
                    expires_at=utcnow() + timedelta(hours=12),
                )
            )
        return token

    def current_user(self, token: str | None) -> dict[str, Any]:
        if not token:
            raise DomainError("Please sign in to continue.", 401)
        with self.db.read() as session:
            login = session.get(LoginSession, sha256(token.encode()).hexdigest())
            if not login or login.expires_at < utcnow():
                raise DomainError("Your session expired. Please sign in again.", 401)
            user = session.get(User, login.user_id)
            if user is None:
                raise DomainError("Account not found.", 401)
            return user_dict(user)

    def logout(self, token: str) -> None:
        with self.db.transaction() as session:
            session.execute(delete(LoginSession).where(LoginSession.token_hash == sha256(token.encode()).hexdigest()))

    def register(self, request: RegisterInput) -> tuple[str, dict[str, Any]]:
        try:
            with self.db.transaction() as session:
                if session.scalar(select(User).where(User.email == request.email)):
                    raise DomainError("An account with this email already exists.", 409)
                user = Repository(session, User).add(
                    User(
                        name=request.name.strip(),
                        email=request.email,
                        password_hash=self.hasher.hash(request.password),
                        role="user",
                    )
                )
                profile = user_dict(user)
        except IntegrityError as exc:
            raise DomainError("An account with this email already exists.", 409) from exc
        return self.issue_session(profile["id"]), profile


class RailService:
    def __init__(self, db: Database, fares: FarePolicy | None = None, payment: PaymentGateway | None = None) -> None:
        self.db = db
        self.fares = fares or StandardFare()
        self.payment = payment or DemoPayment()

    @staticmethod
    def require_admin(session: Session, user_id: int) -> None:
        user = session.get(User, user_id)
        if not user or user.role != "admin":
            raise DomainError("Administrator access required.", 403)

    def stations(self) -> list[dict[str, Any]]:
        with self.db.read() as session:
            return [
                {"code": s.code, "name": s.name, "city": s.city, "lat": s.latitude, "lon": s.longitude}
                for s in session.scalars(select(Station).order_by(Station.city))
            ]

    def seat_map(self, train_id: int, when: date, travel_class: str) -> list[dict[str, Any]]:
        if travel_class not in CLASSES:
            raise DomainError("Choose a valid travel class.")
        with self.db.read() as session:
            train = session.get(Train, train_id)
            if not train:
                raise DomainError("Train not found.", 404)
            inventory = session.get(Inventory, (train_id, when, travel_class))
            capacity = inventory.capacity if inventory else train.capacity
            taken = set(
                session.scalars(
                    select(SeatAssignment.seat_number).where(
                        SeatAssignment.train_id == train_id,
                        SeatAssignment.journey_date == when,
                        SeatAssignment.travel_class == travel_class,
                    )
                )
            )
            return [{"number": n, "taken": n in taken} for n in range(1, capacity + 1)]

    @staticmethod
    def _train_dict(train: Train, stations: dict[str, Station]) -> dict[str, Any]:
        return {
            "id": train.id,
            "number": train.number,
            "name": train.name,
            "origin": train.origin,
            "destination": train.destination,
            "origin_city": stations[train.origin].city,
            "destination_city": stations[train.destination].city,
            "departure": train.departure,
            "arrival": train.arrival,
            "duration": train.duration,
            "base_fare": train.base_fare,
            "capacity": train.capacity,
            "active": train.active,
        }

    @timed
    def search(
        self,
        origin: str = "",
        destination: str = "",
        journey_date: date | None = None,
        travel_class: str = "CC",
        sort: str = "departure",
    ) -> list[dict[str, Any]]:
        if travel_class not in CLASSES:
            raise DomainError("Choose a valid travel class.")
        when = journey_date or today() + timedelta(days=1)
        with self.db.read() as session:
            query = select(Train).where(Train.active.is_(True))
            if origin:
                query = query.where(Train.origin == origin)
            if destination:
                query = query.where(Train.destination == destination)
            stations = {s.code: s for s in session.scalars(select(Station))}
            trains = list(session.scalars(query))
            ids = [t.id for t in trains]
            occupied = (
                dict(
                    session.execute(
                        select(SeatAssignment.train_id, func.count())
                        .where(
                            SeatAssignment.train_id.in_(ids),
                            SeatAssignment.journey_date == when,
                            SeatAssignment.travel_class == travel_class,
                        )
                        .group_by(SeatAssignment.train_id)
                    ).all()
                )
                if ids
                else {}
            )
            capacities = (
                {
                    i.train_id: i.capacity
                    for i in session.scalars(
                        select(Inventory).where(
                            Inventory.train_id.in_(ids),
                            Inventory.journey_date == when,
                            Inventory.travel_class == travel_class,
                        )
                    )
                }
                if ids
                else {}
            )
            result = [
                {
                    **self._train_dict(t, stations),
                    "available": capacities.get(t.id, t.capacity) - occupied.get(t.id, 0),
                    "fare": self.fares.quote(t.base_fare, travel_class, 1)["ticket"],
                }
                for t in trains
            ]
        key = {
            "fare": lambda t: t["fare"],
            "duration": lambda t: t["duration"],
            "departure": lambda t: t["departure"],
        }.get(sort)
        if key is None:
            raise DomainError("Unknown sorting option.")
        return merge_sort(result, key)

    @staticmethod
    def _inventory(session: Session, train_id: int, when: date, travel_class: str) -> tuple[Train, Inventory]:
        # Lock hierarchy is always Train -> Inventory -> Booking. The train lock also
        # makes lazy inventory creation race-free (coarse but adequate for this project).
        train = session.scalar(select(Train).where(Train.id == train_id).with_for_update())
        if train is None:
            raise DomainError("This train does not exist.", 404)
        inventory = session.scalar(
            select(Inventory)
            .where(
                Inventory.train_id == train_id, Inventory.journey_date == when, Inventory.travel_class == travel_class
            )
            .with_for_update()
        )
        if inventory is None:
            inventory = Inventory(
                train_id=train_id, journey_date=when, travel_class=travel_class, capacity=train.capacity
            )
            session.add(inventory)
            session.flush()
        return train, inventory

    @staticmethod
    def _available(session: Session, inventory: Inventory) -> list[int]:
        taken = set(
            session.scalars(
                select(SeatAssignment.seat_number).where(
                    SeatAssignment.train_id == inventory.train_id,
                    SeatAssignment.journey_date == inventory.journey_date,
                    SeatAssignment.travel_class == inventory.travel_class,
                )
            )
        )
        return [n for n in range(1, inventory.capacity + 1) if n not in taken]

    @staticmethod
    def _assign(session: Session, booking: Booking, seats: list[int]) -> None:
        for seat in seats:
            session.add(
                SeatAssignment(
                    train_id=booking.train_id,
                    journey_date=booking.journey_date,
                    travel_class=booking.travel_class,
                    seat_number=seat,
                    booking_pnr=booking.pnr,
                )
            )

    @staticmethod
    def _event(session: Session, booking: Booking, kind: str, message: str) -> None:
        session.add(AuditEvent(user_id=booking.user_id, kind=kind, message=message, booking_pnr=booking.pnr))

    def _booking_dict(self, session: Session, booking: Booking) -> dict[str, Any]:
        train = session.get(Train, booking.train_id)
        assert train is not None
        stations = {
            s.code: s
            for s in session.scalars(select(Station).where(Station.code.in_([train.origin, train.destination])))
        }
        seats = list(
            session.scalars(
                select(SeatAssignment.seat_number)
                .where(SeatAssignment.booking_pnr == booking.pnr)
                .order_by(SeatAssignment.seat_number)
            )
        )
        user = session.get(User, booking.user_id)
        return {
            "pnr": booking.pnr,
            "user_id": booking.user_id,
            "passenger_name": user.name if user else "",
            "train": self._train_dict(train, stations),
            "journey_date": booking.journey_date.isoformat(),
            "travel_class": booking.travel_class,
            "class_name": CLASSES[booking.travel_class],
            "status": booking.status,
            "passengers": booking.passengers,
            "fare": booking.fare,
            "seats": list(seat_labels(seats)),
            "seat_numbers": seats,
            "created_at": booking.created_at.isoformat(),
            "expires_at": booking.expires_at.isoformat() + "Z" if booking.expires_at else None,
            "payment_reference": booking.payment_reference,
        }

    @timed
    def create_booking(self, user_id: int, request: BookingInput) -> dict[str, Any]:
        if not today() <= request.journey_date <= today() + timedelta(days=60):
            raise DomainError("Choose a journey date within the next 60 days.")
        fingerprint = sha256(request.model_dump_json().encode()).hexdigest()
        try:
            with self.db.transaction() as session:
                if session.get(User, user_id) is None:
                    raise DomainError("Please sign in.", 401)
                existing = session.scalar(
                    select(Booking).where(
                        Booking.user_id == user_id, Booking.idempotency_key == request.idempotency_key
                    )
                )
                if existing:
                    if existing.request_hash != fingerprint:
                        raise DomainError("This request key was already used for a different booking.", 409)
                    return self._booking_dict(session, existing)
                train, inventory = self._inventory(
                    session, request.train_id, request.journey_date, request.travel_class
                )
                # Another identical request may have committed while we waited for a lock.
                existing = session.scalar(
                    select(Booking).where(
                        Booking.user_id == user_id, Booking.idempotency_key == request.idempotency_key
                    )
                )
                if existing:
                    if existing.request_hash != fingerprint:
                        raise DomainError("This request key was already used for a different booking.", 409)
                    return self._booking_dict(session, existing)
                if not train.active:
                    raise DomainError("This train is not accepting new bookings.", 409)
                from datetime import datetime
                from zoneinfo import ZoneInfo

                if request.journey_date == today() and train.departure <= datetime.now(
                    ZoneInfo("Asia/Kolkata")
                ).strftime("%H:%M"):
                    raise DomainError("This train has already departed today.")
                waiting = session.scalar(
                    select(Booking.pnr)
                    .where(
                        Booking.train_id == train.id,
                        Booking.journey_date == request.journey_date,
                        Booking.travel_class == request.travel_class,
                        Booking.status == "waitlisted",
                    )
                    .limit(1)
                )
                seats = (
                    []
                    if waiting
                    else allocate_seats(
                        self._available(session, inventory), len(request.passengers), request.preference
                    )
                )
                if not seats and not request.allow_waitlist:
                    raise DomainError("Not enough seats. Try another train or join the waitlist.", 409)
                status = "waitlisted" if not seats else ("confirmed" if request.mode == "book" else "reserved")
                pnr = "RR" + secrets.token_hex(4).upper()
                fare = self.fares.quote(train.base_fare, request.travel_class, len(request.passengers))["total"]
                booking = Repository(session, Booking).add(
                    Booking(
                        pnr=pnr,
                        user_id=user_id,
                        train_id=train.id,
                        journey_date=request.journey_date,
                        travel_class=request.travel_class,
                        status=status,
                        passengers=[p.model_dump() for p in request.passengers],
                        fare=fare,
                        expires_at=utcnow() + timedelta(minutes=15) if status == "reserved" else None,
                        idempotency_key=request.idempotency_key,
                        request_hash=fingerprint,
                        payment_reference=self.payment.pay(fare, pnr) if status == "confirmed" else None,
                    )
                )
                self._assign(session, booking, seats)
                self._event(
                    session,
                    booking,
                    status,
                    f"{pnr} · {len(request.passengers)} passenger(s) · {train.name} · {status}",
                )
                session.flush()
                return self._booking_dict(session, booking)
        except IntegrityError as exc:
            # The unique request key is also a final guard against cross-train races.
            with self.db.read() as session:
                existing = session.scalar(
                    select(Booking).where(
                        Booking.user_id == user_id, Booking.idempotency_key == request.idempotency_key
                    )
                )
                if existing and existing.request_hash == fingerprint:
                    return self._booking_dict(session, existing)
            raise DomainError("Conflicting reservation request. Please try again.", 409) from exc

    def bookings(self, user_id: int, admin: bool = False) -> list[dict[str, Any]]:
        with self.db.read() as session:
            query = select(Booking).order_by(Booking.created_at.desc())
            if admin:
                self.require_admin(session, user_id)
            else:
                query = query.where(Booking.user_id == user_id)
            return [self._booking_dict(session, b) for b in session.scalars(query)]

    def booking(self, user_id: int, pnr: str) -> dict[str, Any]:
        with self.db.read() as session:
            booking = session.get(Booking, pnr)
            if not booking:
                raise DomainError("Ticket not found.", 404)
            user = session.get(User, user_id)
            if booking.user_id != user_id and (not user or user.role != "admin"):
                raise DomainError("This ticket belongs to another account.", 403)
            return self._booking_dict(session, booking)

    def _locked_booking(self, session: Session, pnr: str, user_id: int | None) -> tuple[Booking, Inventory]:
        booking = session.get(Booking, pnr)
        if booking is None:
            raise DomainError("Ticket not found.", 404)
        if user_id is not None and booking.user_id != user_id:
            user = session.get(User, user_id)
            if not user or user.role != "admin":
                raise DomainError("This ticket belongs to another account.", 403)
        _, inventory = self._inventory(session, booking.train_id, booking.journey_date, booking.travel_class)
        booking = session.scalar(
            select(Booking).where(Booking.pnr == pnr).with_for_update().execution_options(populate_existing=True)
        )
        assert booking is not None
        return booking, inventory

    def _promote(self, session: Session, inventory: Inventory) -> None:
        waitlist = deque(
            session.scalars(
                select(Booking)
                .where(
                    Booking.train_id == inventory.train_id,
                    Booking.journey_date == inventory.journey_date,
                    Booking.travel_class == inventory.travel_class,
                    Booking.status == "waitlisted",
                )
                .order_by(Booking.created_at, Booking.pnr)
                .with_for_update()
            )
        )
        available = self._available(session, inventory)
        while waitlist:
            booking = waitlist.popleft()
            seats = allocate_seats(available, len(booking.passengers))
            if not seats:
                break  # FIFO fairness; do not let small groups jump the queue.
            booking.status = "reserved"
            booking.expires_at = utcnow() + timedelta(minutes=15)
            self._assign(session, booking, seats)
            occupied = set(seats)
            available = [seat for seat in available if seat not in occupied]
            self._event(session, booking, "promoted", f"{booking.pnr} · Waitlist promoted. Confirm within 15 minutes.")

    def cancel(self, user_id: int, pnr: str) -> dict[str, Any]:
        with self.db.transaction() as session:
            booking, inventory = self._locked_booking(session, pnr, user_id)
            if booking.status in ("cancelled", "expired"):
                return self._booking_dict(session, booking)
            if booking.journey_date < today():
                raise DomainError("Past journeys cannot be cancelled.", 409)
            booking.status, booking.expires_at = "cancelled", None
            session.execute(delete(SeatAssignment).where(SeatAssignment.booking_pnr == pnr))
            self._event(session, booking, "cancelled", f"{pnr} · Booking cancelled; seats released. Demo refund only.")
            session.flush()
            self._promote(session, inventory)
            session.flush()
            return self._booking_dict(session, booking)

    def confirm(self, user_id: int, pnr: str) -> dict[str, Any]:
        with self.db.transaction() as session:
            booking, _ = self._locked_booking(session, pnr, user_id)
            if booking.status == "confirmed":
                return self._booking_dict(session, booking)
            if booking.status != "reserved" or not booking.expires_at or booking.expires_at <= utcnow():
                raise DomainError("This reservation cannot be confirmed; the hold may have expired.", 409)
            booking.payment_reference = self.payment.pay(booking.fare, pnr)
            booking.status, booking.expires_at = "confirmed", None
            self._event(session, booking, "confirmed", f"{pnr} · Reservation confirmed with simulated payment.")
            session.flush()
            return self._booking_dict(session, booking)

    def expire_holds(self) -> int:
        with self.db.read() as session:
            pnrs = list(
                session.scalars(select(Booking.pnr).where(Booking.status == "reserved", Booking.expires_at <= utcnow()))
            )
        expired = 0
        for pnr in pnrs:
            with self.db.transaction() as session:
                booking, inventory = self._locked_booking(session, pnr, None)
                if booking.status != "reserved" or not booking.expires_at or booking.expires_at > utcnow():
                    continue
                booking.status, booking.expires_at = "expired", None
                session.execute(delete(SeatAssignment).where(SeatAssignment.booking_pnr == pnr))
                self._event(session, booking, "expired", f"{pnr} · Reservation expired; seats released.")
                session.flush()
                self._promote(session, inventory)
                expired += 1
        return expired

    def events(self, user_id: int, admin: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        with self.db.read() as session:
            query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(limit, 100))
            if admin:
                self.require_admin(session, user_id)
            else:
                query = query.where(AuditEvent.user_id == user_id)
            return [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "message": e.message,
                    "pnr": e.booking_pnr,
                    "created_at": e.created_at.isoformat() + "Z",
                }
                for e in session.scalars(query)
            ]

    def admin_stats(self, user_id: int) -> dict[str, Any]:
        bookings = self.bookings(user_id, admin=True)
        active = [b for b in bookings if b["status"] in ("confirmed", "reserved")]
        confirmed = [b for b in bookings if b["status"] == "confirmed"]
        days = [today() - timedelta(days=i) for i in range(6, -1, -1)]
        dates = Counter(local_day(b["created_at"]) for b in bookings)
        revenue = {
            d.isoformat(): sum(b["fare"] for b in confirmed if local_day(b["created_at"]) == d.isoformat())
            for d in days
        }
        counts = Counter(b["status"] for b in bookings)
        with self.db.read() as session:
            return {
                "total_bookings": len(bookings),
                "active_bookings": len(active),
                "revenue": sum(b["fare"] for b in confirmed),
                "active_trains": session.scalar(select(func.count()).select_from(Train).where(Train.active.is_(True))),
                "users": session.scalar(select(func.count()).select_from(User).where(User.role == "user")),
                "waitlisted": counts["waitlisted"],
                "days": [d.strftime("%a") for d in days],
                "daily_bookings": [dates[d.isoformat()] for d in days],
                "daily_revenue": list(revenue.values()),
                "status_counts": dict(counts),
                "bookings": bookings,
            }

    def all_trains(self, user_id: int) -> list[dict[str, Any]]:
        with self.db.read() as session:
            self.require_admin(session, user_id)
            stations = {s.code: s for s in session.scalars(select(Station))}
            return [self._train_dict(t, stations) for t in session.scalars(select(Train).order_by(Train.number))]

    def add_train(self, user_id: int, request: TrainInput) -> dict[str, Any]:
        try:
            with self.db.transaction() as session:
                self.require_admin(session, user_id)
                stations = {s.code: s for s in session.scalars(select(Station))}
                if request.origin not in stations or request.destination not in stations:
                    raise DomainError("Select stations from the station directory.")
                train = Repository(session, Train).add(Train(**request.model_dump(), active=True))
                session.add(
                    AuditEvent(
                        user_id=user_id, kind="train_added", message=f"{train.number} · {train.name} added to network."
                    )
                )
                return self._train_dict(train, stations)
        except IntegrityError as exc:
            raise DomainError("A train with this number already exists.", 409) from exc

    def toggle_train(self, user_id: int, train_id: int) -> bool:
        with self.db.transaction() as session:
            self.require_admin(session, user_id)
            train = session.scalar(select(Train).where(Train.id == train_id).with_for_update())
            if not train:
                raise DomainError("Train not found.", 404)
            train.active = not train.active
            session.add(
                AuditEvent(
                    user_id=user_id,
                    kind="train_updated",
                    message=f"{train.number} · New bookings {'enabled' if train.active else 'paused'}.",
                )
            )
            return train.active

    def graph(self) -> Graph:
        graph: Graph = {}
        with self.db.read() as session:
            for t in session.scalars(select(Train).where(Train.active.is_(True))):
                graph.setdefault(t.origin, []).append(Edge(t.destination, t.base_fare, t.duration, t.number))
        return graph

    def export_bookings_csv(self, user_id: int) -> str:
        import csv
        import io

        bookings = self.bookings(user_id, admin=True)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["PNR", "Passenger", "Train", "Date", "Class", "Status", "Fare_INR"])
        for b in bookings:
            # Prevent spreadsheet-formula injection from user-provided display names.
            safe_name = b["passenger_name"]
            if safe_name.startswith(("=", "+", "-", "@")):
                safe_name = "'" + safe_name
            writer.writerow(
                [
                    b["pnr"],
                    safe_name,
                    b["train"]["number"],
                    b["journey_date"],
                    b["travel_class"],
                    b["status"],
                    b["fare"],
                ]
            )
        return output.getvalue()
