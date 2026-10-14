"""Specification-first input validation shared by API and Python UI."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PassengerInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=1, le=120)
    gender: Literal["Male", "Female", "Other"] = "Other"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter a passenger name of at least two characters.")
        return value


class BookingInput(BaseModel):
    train_id: int = Field(gt=0)
    journey_date: date
    travel_class: Literal["CC", "3A", "SL"] = "CC"
    passengers: list[PassengerInput] = Field(min_length=1, max_length=6)
    mode: Literal["book", "reserve"] = "book"
    allow_waitlist: bool = True
    preference: Literal["any", "window", "together"] = "together"
    idempotency_key: str = Field(min_length=8, max_length=80)


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class RegisterInput(LoginInput):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("email")
    @classmethod
    def email_format(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value.strip().lower()

    @field_validator("name")
    @classmethod
    def name_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter a full name of at least two characters.")
        return value

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Use at least eight characters for your password.")
        return value


class TrainInput(BaseModel):
    number: str = Field(pattern=r"^\d{5}$")
    name: str = Field(min_length=3, max_length=100)
    origin: str
    destination: str
    departure: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    arrival: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration: int = Field(ge=10, le=4320)
    base_fare: int = Field(ge=50, le=15000)
    capacity: int = Field(ge=6, le=120)

    @model_validator(mode="after")
    def valid_route(self) -> "TrainInput":
        if self.origin == self.destination:
            raise ValueError("Origin and destination must be different.")
        self.name = self.name.strip()
        if len(self.name) < 3:
            raise ValueError("Enter a train name of at least three characters.")
        departure = int(self.departure[:2]) * 60 + int(self.departure[3:])
        arrival = int(self.arrival[:2]) * 60 + int(self.arrival[3:])
        if self.duration % 1440 != (arrival - departure) % 1440:
            raise ValueError("Duration must agree with departure and arrival times, including overnight travel.")
        return self
