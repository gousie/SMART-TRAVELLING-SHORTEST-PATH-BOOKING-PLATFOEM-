"""Unit of work + generic repository. PostgreSQL provides cross-process row locks."""

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from threading import RLock
from typing import Generic, TypeVar

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from railora.models import Base

T = TypeVar("T", bound=Base)


class Repository(Generic[T]):
    def __init__(self, session: Session, model: type[T]) -> None:
        self.session, self.model = session, model

    def all(self) -> list[T]:
        return list(self.session.scalars(select(self.model)))

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity


class Database:
    def __init__(self, url: str) -> None:
        self.is_sqlite = url.startswith("sqlite")
        kwargs = (
            {"connect_args": {"check_same_thread": False, "timeout": 30}} if self.is_sqlite else {"pool_pre_ping": True}
        )
        self.engine = create_engine(url, **kwargs)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.lock = RLock()
        if self.is_sqlite:

            @event.listens_for(self.engine, "connect")
            def _sqlite_pragmas(connection, _record):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def read(self) -> Iterator[Session]:
        with self.sessions() as session:
            yield session

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        # SQLite fallback is for a SINGLE-process demo only; PostgreSQL uses row locks.
        with self.lock if self.is_sqlite else nullcontext():
            with self.sessions.begin() as session:
                yield session
