"""Run with python main.py. Python owns both the UI and the backend."""

import asyncio
import logging
import os
import secrets

from railora.config import ROOT, settings

# UI session files contain authentication state and are intentionally not bundled.
os.environ.setdefault("NICEGUI_STORAGE_PATH", str(ROOT / ".cache" / "ui-storage"))
from pathlib import Path

Path(os.environ["NICEGUI_STORAGE_PATH"]).mkdir(parents=True, exist_ok=True)


def main() -> None:
    from nicegui import app, run, ui

    from railora.api import domain_error_handler, make_router
    from railora.db import Database
    from railora.seed import seed_demo
    from railora.services import AuthService, DomainError, RailService
    from railora.web import register_pages

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    db = Database(settings.database_url)
    db.create_schema()
    auth = AuthService(db)
    if settings.seed_demo:
        seed_demo(db, auth)
    rail = RailService(db)
    app.add_static_files("/static", ROOT / "railora" / "static")
    app.include_router(make_router(auth, rail))
    app.add_exception_handler(DomainError, domain_error_handler)
    register_pages(auth, rail)
    tasks = []

    async def housekeeping():
        while True:
            try:
                await run.io_bound(rail.expire_holds)
            except Exception:
                logging.exception("Reservation expiry worker failed")
            await asyncio.sleep(15)

    async def startup():
        tasks.append(asyncio.create_task(housekeeping()))

    async def shutdown():
        for task in tasks:
            task.cancel()
        db.engine.dispose()

    app.on_startup(startup)
    app.on_shutdown(shutdown)
    if not settings.storage_secret:
        logging.warning("STORAGE_SECRET missing: using an ephemeral development-only secret")
    ui.run(
        host="0.0.0.0",
        port=settings.port,
        title="Railora · Journeys made simple",
        favicon=ROOT / "railora" / "static" / "favicon.svg",
        reload=False,
        show=False,
        storage_secret=settings.storage_secret or secrets.token_urlsafe(48),
        fastapi_docs=True,
        uvicorn_logging_level="info",
        reconnect_timeout=20,
    )


if __name__ == "__main__":
    main()
