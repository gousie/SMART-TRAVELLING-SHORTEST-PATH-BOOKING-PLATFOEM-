# Specification: railway reservation as a computational problem

## 1. Real-world problem

A traveler needs to discover a suitable train, understand fares and available seats, reserve a group without conflicting with another buyer, receive a ticket and manage changes. An operator needs consistent inventory, a trustworthy record of transactions and a clear view of reservations.

The difficult part is not the booking button. It is preserving **one-seat/one-active-assignment** when requests, retries, cancellations and expiry occur concurrently.

### Scope

Build an academic direct-route reservation system with simulated payments and synthetic railway inventory. No real ticket issuance, regulated payment processing, IRCTC connectivity or government ID collection is in scope.

## 2. Decomposition

| Subproblem | Input | Output / invariant | Implementation |
|---|---|---|---|
| Identity and roles | Email/password | Hashed credentials; expiring session; role checked | `AuthService` |
| Station discovery | Station directory | Valid codes and display labels | `Station`, `RailService.stations` |
| Search | Origin, destination, date, class, sort | Only active direct services; calculated free seats | `RailService.search` |
| Pricing | Base fare, class, passenger count | Exact integer-rupee breakdown | `FarePolicy`, `fare_quote` |
| Group allocation | Available seats, size, preference | Unique free seats, preferably contiguous | `allocate_seats` |
| Reservation transaction | Valid passengers + idempotency key | Atomic booking, seat assignments and event | `create_booking` |
| Waitlist | Capacity shortage | FIFO groups; no queue jumping | `Booking.status`, `_promote`, deque |
| Cancellation / expiry | PNR / hold deadline | Release seats; promote feasible head groups | `cancel`, `expire_holds` |
| Payment simulation | Reservation + amount | Demo receipt only; no charge/card data | `DemoPayment` |
| Administration | Authorized operator | Charts, register, train control, audit events | `AdminUI`, admin service methods |
| Teaching network | Directed weighted station graph | Inspectable algorithm path and metrics | `/routes`, `/lab` |
| Quality | Invariants and test cases | Reproducible tests and review evidence | `tests/`, `reports/` |

## 3. Abstraction

- **Station:** unique code, name, city and illustrative geographic coordinates.
- **Train:** one sample direct service with number, endpoints, times, duration and a base fare.
- **Inventory:** capacity for `(train, journey_date, class)`.
- **Seat assignment:** one seat number scoped to that inventory, linked to a booking.
- **Booking:** PNR, owner, passengers, status, exact fare, deadline and request fingerprint.
- **User:** identity and role, separate from passenger names.
- **Audit event:** a persistent, transactionally recorded change, not an outgoing email.
- **Graph:** stations as nodes, train services as weighted directed edges. It deliberately leaves out connection feasibility and partial segments.

Coach rows of six seats are a **simulation**, not a statement about the layout of every real railway coach.

## 4. Pattern recognition

- Repeated ordering questions → reusable stable sorting with a key function.
- Cheapest non-negative network route → shortest-path/greedy frontier.
- Maximum permitted legs → layered dynamic programming.
- Adjacent group seats → constrained backtracking with pruning.
- Fastest route within a fare budget → constrained search with branch-and-bound.
- Reservation retries → idempotent command handling and a uniqueness constraint.
- Shared scarce resources → transaction + row locks, not just async functions.
- Waiting customers → FIFO queue discipline; head-of-line blocking is a deliberate fairness choice.

## 5. Functional requirements

**FR1:** Registration creates traveler accounts only. A request cannot choose the administrator role.

**FR2:** Travelers may access and change their own tickets. Administrators may inspect tickets and change train availability.

**FR3:** Search offers direct active routes and reports capacity minus committed assignments for the requested date/class.

**FR4:** A booking contains 1–6 passengers with names, ages 1–120, class, journey date, preference, mode and request key.

**FR5:** Dates are within today through 60 days ahead. A train that has already departed today cannot be newly booked.

**FR6:** A book command confirms available seats with a simulated receipt. A reserve command holds seats for 15 minutes. A full service may create an uncharged waitlist entry.

**FR7:** A repeated identical request returns the original PNR. Reusing its key with different data fails.

**FR8:** Cancellation/expiry releases assignments and can promote waitlisted groups. Promoted groups receive a new 15-minute hold and must explicitly confirm.

**FR9:** A hold cannot be confirmed once its deadline has passed, even before the expiry sweep runs.

**FR10:** Admin changes and reservations produce persistent audit events. The admin browser checks for newer events every three seconds; NiceGUI pushes refreshed components to the browser.

**FR11:** PDF tickets and CSV export are available and visibly marked as academic/simulated.

**FR12:** Interactive algorithm demonstrations provide actual outputs and measured timings, not fixed example results.

## 6. Safety and correctness invariants

1. At most one active assignment exists for `(train_id, date, class, seat_number)` — database composite primary key.
2. Every assigned seat lies within the inventory range — service allocation.
3. A booking, its seats and its event commit or roll back together — unit of work.
4. Canceled/expired bookings do not retain assignments through service operations.
5. A `(user_id, idempotency_key)` identifies one command result — unique constraint + fingerprint.
6. A payment-provider exception leaves no partially committed booking.
7. Admin mutations require an administrator; PNR access requires ownership or administrator role.
8. Waiting groups are not bypassed by smaller new arrivals.
9. Money is represented as integer rupees; class multiplication rounds rational arithmetic explicitly.
10. Frontend display state is not a substitute for service/database validation.

## 7. Booking state machine

```text
available seats ── book ────────────────> confirmed
available seats ── reserve ─────────────> reserved ── confirm before deadline ──> confirmed
                                               └── deadline sweep ─────────> expired
no seats / existing queue ──────────────> waitlisted ── capacity opens ──────> reserved
confirmed / reserved / waitlisted ── cancel ───────────────────────────────> cancelled
```

Canceled/expired cancellation retries are idempotent. Confirmed confirmation retries are idempotent. No financial refund or real payment is performed.

## 8. Non-functional requirements

- Responsive layouts at mobile and desktop viewport sizes.
- Locally served photography, styles, fonts and browser renderer assets.
- Parametrized ORM queries, strong password hashes, server-side UI tokens and database-stored token hashes.
- Explicit PostgreSQL configuration for database `CTPDB`; development password `root` must be changed outside a demo.
- Type checking for core modules, lint/format checks, isolated testing and actual performance measurement.
- No fabricated external integrations, production claims or test results.

## 9. Acceptance workflow

Sign in as traveler → search → inspect seats/fare → book → see new PNR and PDF → observe the same PNR in a separate admin session → cancel → confirm seats are free → run property/race tests → execute algorithm lab → explain one trade-off and one limitation.
