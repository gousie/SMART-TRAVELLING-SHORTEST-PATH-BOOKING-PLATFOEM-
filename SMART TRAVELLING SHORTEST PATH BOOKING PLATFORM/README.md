# Railora — journeys made simple

A polished **Python-first railway reservation and ticket-booking project** for Computational Thinking and Programming. The frontend is authored in **NiceGUI/Python**, the REST API uses **FastAPI**, and persistence uses **SQLAlchemy + PostgreSQL**.

> **Academic simulation only.** Train names/numbers, timetables, availability and fares are sample data, not verified real services. Payments, refunds and tickets are simulated. No real reservation is issued. This is not affiliated with Indian Railways or IRCTC.

## What you can do

- Sign in, register a traveler, switch between traveler and administrator demo accounts.
- Search direct trains by station, date and class; sort by fare, departure or duration.
- Add 1–6 passengers, request a seat preference, **book now** or **reserve for 15 minutes**.
- See actual database-backed seat availability, view your bookings, cancel or confirm a hold, and download a **PDF demo e-ticket**.
- Join a FIFO waitlist; cancellation or hold expiry can promote waiting groups into a 15-minute reservation.
- Save routes in server-side storage tied to your browser session.
- Use the admin dashboard: live charts, reservation register, CSV export, persistent audit events, train creation and pause/resume controls.
- Explore an illustrative station network and run **greedy, DP, branch-and-bound and seat-allocation demonstrations** in the interactive Algorithm lab.

The interface includes a responsive sidebar, scenic train backgrounds, destination photography, ticket cards and ECharts visualisations. Photos and fonts are **self-hosted** for reliable loading; assets are not scraped or hotlinked from Google Images. See [asset credits](docs/ASSET_CREDITS.md).

## Demo accounts

| Workspace | Email | Password |
|---|---|---|
| Traveler | `aditya@railora.demo` | `Railora@123` |
| Administrator | `admin@railora.demo` | `Admin@123` |

These are **public development accounts**. Do not deploy a public production service with seeded credentials or `DEMO_AUTOSIGNIN=true`.

## Run locally with PostgreSQL

Use **Python 3.13** (the version used for validation) and PostgreSQL 17 or a compatible PostgreSQL installation.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Create your database in psql or pgAdmin:

```sql
CREATE DATABASE "CTPDB";
```

The quotes preserve the uppercase name. The supplied configuration assumes PostgreSQL user `postgres`, your requested development password `root`, and port `5432`. Change the username/host if your installation differs. **Never use `root` as a production database password.**

Copy `.env.example` to `.env`, set `STORAGE_SECRET` to a random value, and verify:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:root@localhost:5432/CTPDB
SEED_DEMO=true
DEMO_AUTOSIGNIN=false
PORT=8080
```

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python main.py
```

Open **http://localhost:8080**. The application creates its schema and sample data on first start. A database failure is reported; it does **not** silently switch databases. The hosted preview for this project uses PostgreSQL `CTPDB` and enables traveler autosignin solely to make the demonstration immediately visible.

### Docker Compose alternative

```bash
# Copy .env.example to .env and replace STORAGE_SECRET first.
docker compose up --build
```

Compose creates PostgreSQL **CTPDB**, applies the sample schema, and serves the app on port 8080. PostgreSQL is exposed only on the local loopback interface. Do not run Compose's database on port 5432 while another local PostgreSQL instance already owns it. Docker configuration is included; it was **not executed in the delivery sandbox**.

### Explicit SQLite fallback

For a single-process demonstration without PostgreSQL, deliberately set:

```dotenv
DATABASE_URL=sqlite:///./railora-demo.db
```

SQLite uses a process-local lock. It is **not** the recommended deployment backend and does not demonstrate cross-process PostgreSQL row-lock semantics.

## Pages and API

| Page | URL |
|---|---|
| User dashboard | `/dashboard` |
| Login / registration | `/login`, `/register` |
| Train search / booking | `/search` |
| My bookings / saved routes | `/bookings`, `/saved` |
| Station network / algorithm lab | `/routes`, `/lab` |
| Admin dashboard | `/admin` |
| Admin trains / reservations / audit feed | `/admin/trains`, `/admin/bookings`, `/admin/activity` |
| REST API docs / health | `/docs`, `/api/health` |

UI and REST API call the **same application services**. API clients log in at `POST /api/login`, then send the returned token as `Authorization: Bearer <token>`. Tokens are stored hashed in the database. UI sessions keep tokens on the server, not in client-side application state.

## Quality checks

```bash
ruff check .
ruff format --check .
mypy
pytest --cov --cov-report=term-missing
```

The Mypy configuration checks seven core modules. Statement coverage includes core backend/algorithms/ticket generation; dynamic UI and synthetic seeding are explicitly excluded. Browser interactions are validated separately.

**PostgreSQL integration and race tests** require an isolated test database. Never use your application database as a test database:

```sql
CREATE DATABASE "CTPDB_test";
```

```bash
# macOS/Linux; PowerShell: $env:TEST_DATABASE_URL="..."
export TEST_DATABASE_URL='postgresql+psycopg://postgres:root@localhost:5432/CTPDB_test'
pytest --cov --cov-report=term-missing
```

The fixture refuses non-SQLite database names that do not end in `_test`. Tests rebuild the test schema; do not place valuable data in that database. Do not run the destructive DB fixture concurrently against the same database using pytest-xdist.

**Browser end-to-end tests:** start a disposable seeded demo instance, then in another terminal:

```bash
python -m playwright install --with-deps chromium
# macOS/Linux; PowerShell: $env:RAILORA_E2E_URL="http://localhost:8080"
export RAILORA_E2E_URL=http://localhost:8080
pytest tests/test_e2e.py -v
```

Browser tests sign in, book a ticket, see it arrive in the live admin dashboard, download the PDF, cancel the test booking, check mobile navigation, and execute the process-pool algorithm lab. They mutate demo data. Never point them at a real production service.

```bash
python scripts/benchmark.py
# Optional, read-only local database timings as well:
python scripts/benchmark.py --database
```

This writes repeatable algorithm timings, Python-heap allocation observations, and measured merge-sort comparisons to `reports/performance.json` and `reports/performance.csv`. See [validation results](docs/VALIDATION.md) for the actual executed checks, coverage scope and limitations.

## Project structure

```text
main.py                  App entrypoint + reservation-expiry async worker
railora/
  web.py                 Python traveler/login frontend
  admin_ui.py            Python operations frontend
  lab_ui.py              Interactive computational-thinking lab
  web_components.py      Reusable Python UI components and embedded SVGs
  api.py                 REST endpoints and error translation
  services.py            Booking/auth services, fare/payment strategies
  algorithms.py          Pure typed algorithms, generator and decorator
  schemas.py             Pydantic input specifications
  models.py              SQLAlchemy entities and DB constraints
  db.py                  Context-managed unit of work + generic repository
  seed.py                Deterministic synthetic dataset
  tickets.py             PDF demo ticket generation
  static/                Local CSS, font, SVG and licensed web photos
 tests/                  Unit, property, API, race and browser tests
 scripts/                Performance evaluation / administrator setup
 docs/                   Specification, assessment map, algorithms, defence
 reports/                Actual validation reports
 .github/workflows/      CI configuration (quality, PostgreSQL, container build)
 Dockerfile              Non-root application container
 docker-compose.yml      PostgreSQL + application
```

## Assessment and technical defence

Start with [the assessment map](docs/ASSESSMENT_MAP.md), then read:

1. [Problem specification and decomposition](docs/SPECIFICATION.md)
2. [Architecture and concurrency decisions](docs/ARCHITECTURE.md)
3. [Algorithms, data structures and complexity](docs/ALGORITHMS.md)
4. [Technical-defence questions and live-demo script](docs/TECHNICAL_DEFENCE.md)
5. [AI-assisted review and validation record](docs/AI_REVIEW.md)

A student should be able to explain the code, alter one requirement, add a test and rerun validation. Generated code and passing tests are evidence, **not a substitute for understanding**.

## Deliberate limitations

- Direct origin-to-destination booking only; no intermediate-segment inventory model.
- The station-graph planner is educational: it does not validate connections, operating days or station-transfer times.
- All sample trains offer three simulated classes; no claim of real coach composition is made.
- No real payments, SMS/email, government ID verification, railway API or account recovery provider.
- Reservation expiry is eventually applied by a 15-second background sweep; confirmation independently rejects expired holds.
- Train-level locking is intentionally coarse. NiceGUI runs in one application process here; horizontally scaled UI state would need shared storage and operational changes.
- Production readiness would require hardened TLS/proxy configuration, rate limits, operational monitoring, migrations, real payments and webhooks, backup/restore, security review, accessibility auditing and official railway integration.
