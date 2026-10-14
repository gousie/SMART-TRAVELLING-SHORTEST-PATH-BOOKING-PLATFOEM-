# Architecture, OOP and concurrency

## Python on both sides

NiceGUI page composition, state and browser event handlers are authored in Python. NiceGUI necessarily supplies Vue/Quasar/JavaScript browser rendering internally; the claim is **Python-authored frontend**, not that a browser executes native Python. Styling uses local CSS, SVG and locally cached web photos.

```text
Browser
  └─ NiceGUI components + WebSocket updates
       └─ Python RailUI / AdminUI / LabUI
            ├─ AuthService
            └─ RailService ──────────────┐
API clients ── FastAPI routes ───────────┤
                                        ├─ FarePolicy / StandardFare
                                        ├─ PaymentGateway / DemoPayment
                                        ├─ pure algorithms
                                        └─ Database unit of work
                                              └─ SQLAlchemy
                                                   └─ PostgreSQL CTPDB
```

The UI does not call localhost from the user's browser to reach another backend. The API and UI share one server and relative asset URLs. The server binds `0.0.0.0` for a hosted reverse-proxy preview.

## Object-oriented design

- **Abstraction:** `FarePolicy` is an abstract base class defining a quote contract.
- **Inheritance:** `StandardFare` implements `FarePolicy`; ORM entities inherit the declarative `Base`.
- **Composition:** `RailService` receives a database, fare policy and payment provider. It does not inherit all their behavior.
- **Structural interface:** `PaymentGateway` is a `Protocol`. A test provider can be injected without changing booking code.
- **Strategy pattern:** price/payment behavior is replaceable. Real payments would need a different architecture, not simply a synchronous network call under a database lock.
- **Repository pattern:** `Repository[T]` demonstrates generic, typed entity persistence.
- **Unit of work:** context-managed transactions establish one commit/rollback boundary.
- **Application services:** UI and REST endpoints share business rules and authorization; no duplicated browser-only validation.
- **Immutability:** graph edges, route results and settings use frozen dataclasses.

## Functional design

`merge_sort`, `fare_quote`, `allocate_seats`, and graph algorithms are deterministic pure functions for their inputs. `merge_sort` accepts a higher-order key function. Comprehensions filter/transform records. `seat_labels` is a lazy generator implementing iterator protocol behavior. `timed` is a metadata-preserving decorator using `ParamSpec` and return generics.

Side effects are isolated to services, database access, PDF generation and UI event handlers. This permits property-based testing without a web server.

## Relational model

```text
users ──< login_sessions
users ──< bookings >── trains >── stations (origin and destination)
trains ──< inventory (train + date + class)
bookings ──< seat_assignments (train + date + class + seat primary key)
users/bookings ──< audit_events
```

- Station codes and train numbers are unique.
- Seat identity is a composite primary key.
- Inventory uses a composite primary key.
- Booking command identity is unique per user.
- Route search, date/status filtering and FIFO waitlist lookup have relevant indexes.
- Passwords are Argon2 hashes, not plaintext.
- Session bearer tokens are random; only SHA-256 token fingerprints are stored in PostgreSQL.

SQLAlchemy `create_all` bootstraps this first-version project. It is **not a migration system**. A production upgrade path should introduce Alembic migrations and test backup/restore.

## Race-free booking transaction

1. Check user and request fingerprint.
2. Lock the `Train` row with `SELECT ... FOR UPDATE`.
3. Lock/create the matching inventory. The train lock serializes lazy creation.
4. Recheck idempotency after acquiring the lock.
5. Check active service and departure/date rules.
6. Read committed assignments and the existing waitlist.
7. Allocate free seats or add a waitlisted group.
8. Insert booking, assignments and audit event in the same transaction.
9. Commit; only committed events are later visible to admin readers.

The lock order for related operations is always **Train → Inventory → Booking**. Train-level locking is coarse but simple and safe for this academic workload. It serializes different dates/classes of the same train unnecessarily; pre-created inventory and inventory-only locks are a future throughput improvement. PostgreSQL locks work across service instances; a Python mutex alone would not.

The composite assignment key is a second database-level guard. The unique request key is a final guard against cross-inventory idempotency races.

## Choosing concurrency mechanisms

| Workload | Mechanism used | Why |
|---|---|---|
| SQL queries / synchronous service calls | NiceGUI `run.io_bound` thread pool | Avoid blocking the asyncio event loop |
| Independent dashboard reads | `asyncio.gather` | Coordinate concurrent I/O without pretending that async is a data lock |
| Algorithm lab computation | NiceGUI `run.cpu_bound` process pool | Isolate pure CPU work; use picklable top-level functions |
| Reservation expiry | Async background task + thread-offloaded transaction | Periodic work with controlled startup/shutdown |
| Race-test workload | `ThreadPoolExecutor` | Many simultaneous requests on separate SQL connections |
| FastAPI synchronous routes | Framework-managed worker threads | Standard synchronous DB session ownership per request |

Password verification includes CPU-bound native Argon2 work and a database read. It is thread-offloaded to keep the UI responsive; native-library execution may release the GIL. That is different from claiming Python CPU loops speed up in threads.

### GIL and process implications

On the normal CPython build used here, the GIL limits simultaneous Python bytecode execution in one process. Threads are suitable for blocking I/O; processes can parallelize pure Python CPU work. Process start/serialization overhead can greatly exceed computation time for a 12-station graph, so the lab's process pool is a **mechanism demonstration**, not a speedup claim. No live SQL session/ORM entity is sent to a child process.

### Async limitations

- Async concurrency is not mutual exclusion for scarce seats.
- The expiry sweep runs every 15 seconds; actual release can lag the deadline. Confirmation independently checks the deadline.
- Admin updates use a three-second polling check and NiceGUI WebSocket component delivery, not a broker or guaranteed push notification service.
- Multiple NiceGUI application workers would require coordinated/shared UI storage and deployment changes. This delivery runs one web process.
- SQLite fallback has only a process-local `RLock`; use PostgreSQL to demonstrate cross-process consistency.

## Security boundaries and further work

The service rechecks roles/ownership, validates input through Pydantic and uses parameterized SQL. Public development accounts and prefilled passwords are intentional demo features. No card details or real government IDs are collected.

Before public production use: remove demo accounts/autosignin, configure TLS and secure cookies/proxy trust, add authentication rate limiting and recovery, monitor events, use a dedicated least-privilege DB account, rotate secrets, add migrations/backups, audit accessibility and dependencies, and integrate official rail/payment providers with a transactional outbox and webhook reconciliation. These are not claimed as completed features.
