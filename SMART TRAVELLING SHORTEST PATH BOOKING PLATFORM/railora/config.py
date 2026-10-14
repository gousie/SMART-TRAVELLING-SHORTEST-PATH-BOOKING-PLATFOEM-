"""Environment-driven settings. Secrets never belong in browser code."""

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def today() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_day(utc_iso: str) -> str:
    """Bucket persisted UTC timestamps into the travel workspace's Indian calendar day."""
    instant = datetime.fromisoformat(utc_iso).replace(tzinfo=timezone.utc)
    return instant.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:root@localhost:5432/CTPDB")
    storage_secret: str = os.getenv("STORAGE_SECRET", "")
    demo_autosignin: bool = os.getenv("DEMO_AUTOSIGNIN", "false").lower() == "true"
    seed_demo: bool = os.getenv("SEED_DEMO", "true").lower() == "true"
    port: int = int(os.getenv("PORT", "8080"))


settings = Settings()
