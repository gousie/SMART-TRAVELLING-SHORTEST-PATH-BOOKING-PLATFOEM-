"""Relational entities and database-enforced reservation invariants."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from railora.config import utcnow


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(12), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (CheckConstraint("role IN ('user','admin')", name="valid_role"),)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Station(Base):
    __tablename__ = "stations"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float]
    longitude: Mapped[float]


class Train(Base):
    __tablename__ = "trains"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(5), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    origin: Mapped[str] = mapped_column(ForeignKey("stations.code"))
    destination: Mapped[str] = mapped_column(ForeignKey("stations.code"))
    departure: Mapped[str] = mapped_column(String(5))
    arrival: Mapped[str] = mapped_column(String(5))
    duration: Mapped[int] = mapped_column(Integer)
    base_fare: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer, default=36)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("origin <> destination", name="different_stations"),
        CheckConstraint("base_fare > 0 AND duration > 0 AND capacity > 0", name="positive_train_values"),
        Index("ix_train_route", "origin", "destination", "active"),
    )


class Inventory(Base):
    __tablename__ = "inventory"
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), primary_key=True)
    journey_date: Mapped[date] = mapped_column(Date, primary_key=True)
    travel_class: Mapped[str] = mapped_column(String(4), primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint("capacity > 0", name="positive_inventory"),)


class Booking(Base):
    __tablename__ = "bookings"
    pnr: Mapped[str] = mapped_column(String(12), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"))
    journey_date: Mapped[date] = mapped_column(Date, index=True)
    travel_class: Mapped[str] = mapped_column(String(4))
    status: Mapped[str] = mapped_column(String(16), index=True)
    passengers: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    fare: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    payment_reference: Mapped[str | None] = mapped_column(String(60), nullable=True)
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_booking_request"),
        CheckConstraint(
            "status IN ('confirmed','reserved','waitlisted','cancelled','expired')", name="valid_booking_status"
        ),
        CheckConstraint("fare > 0", name="positive_booking_fare"),
        Index("ix_waitlist_fifo", "train_id", "journey_date", "travel_class", "status", "created_at"),
    )


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id"), primary_key=True)
    journey_date: Mapped[date] = mapped_column(Date, primary_key=True)
    travel_class: Mapped[str] = mapped_column(String(4), primary_key=True)
    seat_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_pnr: Mapped[str] = mapped_column(ForeignKey("bookings.pnr"), index=True)
    __table_args__ = (CheckConstraint("seat_number > 0", name="positive_seat_number"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(String(240))
    booking_pnr: Mapped[str | None] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
