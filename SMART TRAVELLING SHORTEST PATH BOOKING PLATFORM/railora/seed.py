"""Idempotent, clearly synthetic academic data. No live railway API is used."""

import random
from datetime import timedelta

from sqlalchemy import select

from railora.algorithms import fare_quote
from railora.config import today, utcnow
from railora.db import Database
from railora.models import AuditEvent, Booking, Inventory, SeatAssignment, Station, Train, User
from railora.services import AuthService

STATIONS = [
    ("NDLS", "New Delhi", "New Delhi", 28.64, 77.22),
    ("AGC", "Agra Cantt", "Agra", 27.16, 78.00),
    ("JP", "Jaipur Junction", "Jaipur", 26.92, 75.79),
    ("BZA", "Vijayawada Junction", "Vijayawada", 16.52, 80.62),
    ("SC", "Secunderabad Junction", "Hyderabad", 17.43, 78.50),
    ("GNT", "Guntur Junction", "Guntur", 16.30, 80.44),
    ("MAS", "Chennai Central", "Chennai", 13.08, 80.27),
    ("SBC", "KSR Bengaluru", "Bengaluru", 12.98, 77.57),
    ("MAO", "Madgaon Junction", "Goa", 15.27, 73.96),
    ("CSMT", "Chhatrapati Shivaji Terminus", "Mumbai", 18.94, 72.84),
    ("VSKP", "Visakhapatnam", "Visakhapatnam", 17.72, 83.29),
    ("ERS", "Ernakulam Junction", "Kochi", 9.97, 76.29),
]
TRAINS = [
    ("12002", "Shatabdi Express", "NDLS", "AGC", "06:00", "07:57", 117, 595),
    ("20172", "Vande Bharat Express", "NDLS", "AGC", "14:40", "16:20", 100, 810),
    ("12280", "Taj Express", "NDLS", "AGC", "07:10", "10:05", 175, 395),
    ("12616", "Grand Trunk Express", "NDLS", "AGC", "18:50", "21:25", 155, 460),
    ("20833", "Vande Bharat Express", "BZA", "SC", "10:05", "14:15", 250, 1020),
    ("12759", "Charminar Express", "BZA", "SC", "23:15", "05:10", 355, 480),
    ("12733", "Narayanadri Express", "GNT", "SC", "22:10", "05:40", 450, 415),
    ("12014", "Ajmer Shatabdi", "NDLS", "JP", "06:10", "10:40", 270, 725),
    ("12986", "Jaipur Double Decker", "NDLS", "JP", "17:35", "22:00", 265, 650),
    ("12007", "Shatabdi Express", "MAS", "SBC", "06:00", "10:45", 285, 720),
    ("10103", "Mandovi Express", "CSMT", "MAO", "07:10", "19:00", 710, 590),
    ("12677", "Intercity Express", "SBC", "ERS", "06:10", "16:55", 645, 480),
    ("12711", "Pinakini Express", "BZA", "MAS", "06:00", "13:20", 440, 580),
    ("12841", "Coromandel Express", "MAS", "VSKP", "07:00", "19:00", 720, 920),
    ("12627", "Karnataka Express", "SBC", "NDLS", "19:20", "10:30", 2350, 1540),
]


def seed_demo(db: Database, auth: AuthService) -> None:
    with db.transaction() as session:
        if session.scalar(select(User.id).limit(1)):
            return
        for code, name, city, lat, lon in STATIONS:
            session.add(Station(code=code, name=name, city=city, latitude=lat, longitude=lon))
        session.flush()
        admin = User(
            name="Ananya Rao", email="admin@railora.demo", role="admin", password_hash=auth.hasher.hash("Admin@123")
        )
        traveler = User(
            name="Aditya Sharma",
            email="aditya@railora.demo",
            role="user",
            password_hash=auth.hasher.hash("Railora@123"),
        )
        session.add_all([admin, traveler])
        session.flush()
        others = []
        password = auth.hasher.hash("Railora@123")
        for index, name in enumerate(
            [
                "Priya Mehta",
                "Rahul Verma",
                "Neha Reddy",
                "Arjun Patel",
                "Kavya Nair",
                "Vikram Singh",
                "Meera Joshi",
                "Rohit Kumar",
            ]
        ):
            user = User(name=name, email=f"demo{index}@railora.demo", role="user", password_hash=password)
            session.add(user)
            others.append(user)
        session.flush()
        trains = []
        for number, name, origin, destination, departure, arrival, duration, fare in TRAINS:
            train = Train(
                number=number,
                name=name,
                origin=origin,
                destination=destination,
                departure=departure,
                arrival=arrival,
                duration=duration,
                base_fare=fare,
                capacity=36,
            )
            session.add(train)
            trains.append(train)
        session.flush()
        rng = random.Random(42)
        specifications = [(traveler, 0, 1, 2), (traveler, 7, 4, 1), (traveler, 9, -12, 1), (traveler, 10, -30, 2)]
        for i in range(42):
            specifications.append(
                (others[i % len(others)], rng.randrange(len(trains)), rng.randint(-6, 12), rng.randint(1, 3))
            )
        for i, (user, train_index, delta, size) in enumerate(specifications):
            train = trains[train_index]
            when = today() + timedelta(days=delta)
            key = (train.id, when, "CC")
            inventory = session.get(Inventory, key)
            if inventory is None:
                inventory = Inventory(train_id=train.id, journey_date=when, travel_class="CC", capacity=36)
                session.add(inventory)
                session.flush()
            taken = set(
                session.scalars(
                    select(SeatAssignment.seat_number).where(
                        SeatAssignment.train_id == train.id,
                        SeatAssignment.journey_date == when,
                        SeatAssignment.travel_class == "CC",
                    )
                )
            )
            seats = [n for n in range(1, 37) if n not in taken][:size]
            pnr = f"RR{20260000 + i:08d}"
            created = utcnow() - timedelta(days=(0 if i < 2 else rng.randint(0, 6)), hours=rng.randint(0, 3))
            passengers = [{"name": user.name, "age": 24 + i % 30, "gender": "Other"} for _ in range(size)]
            status = (
                "cancelled"
                if i >= 4 and i % 8 == 0
                else ("reserved" if i >= 4 and i % 7 == 0 and delta >= 0 else "confirmed")
            )
            booking = Booking(
                pnr=pnr,
                user_id=user.id,
                train_id=train.id,
                journey_date=when,
                travel_class="CC",
                status=status,
                passengers=passengers,
                fare=fare_quote(train.base_fare, "CC", size)["total"],
                created_at=created,
                expires_at=utcnow() + timedelta(minutes=15) if status == "reserved" else None,
                idempotency_key=f"seed-{i:08d}",
                request_hash="seed",
                payment_reference=f"DEMO-{pnr}" if status == "confirmed" else None,
            )
            session.add(booking)
            session.flush()
            for seat in seats if status != "cancelled" else []:
                session.add(
                    SeatAssignment(
                        train_id=train.id, journey_date=when, travel_class="CC", seat_number=seat, booking_pnr=pnr
                    )
                )
            session.add(
                AuditEvent(
                    user_id=user.id,
                    kind=status,
                    booking_pnr=pnr,
                    message=f"{pnr} · {user.name} · {train.name} · {status}. Synthetic demo data.",
                    created_at=created,
                )
            )
            session.flush()
