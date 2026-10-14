# Railora technical defence and live demonstration

## A 10-minute demonstration

### 0–2 minutes: define the problem

Show the specification. Explain why allocating shared seats is different from displaying a search result. Identify search, pricing, allocation, payment simulation, booking state and audit updates as independent responsibilities.

State the scope clearly: academic sample timetables, no real railway reservation or payment, direct routes only.

### 2–4 minutes: traveler flow

1. Open `/login` and sign in as the traveler.
2. Search New Delhi → Agra tomorrow, AC Chair Car.
3. Change the sort to Lowest fare; explain merge-sort's higher-order key.
4. Open a train, inspect actual seat occupancy and integer-rupee fare breakdown.
5. Add a second passenger and choose Keep us together.
6. Confirm the simulated booking; note the PNR.
7. Open My bookings and download the visibly marked PDF demo e-ticket.

### 4–5 minutes: separate administrator session

Use another browser profile/private window — not merely another tab with the same session cookie. Sign in as administrator.

1. Keep `/admin` open while a traveler submits a new ticket.
2. Within roughly three seconds, observe the new PNR and event.
3. Search the register, export CSV and show train pause/resume.
4. Explain that pausing a train stops **new** bookings; it does not silently cancel existing tickets.

### 5–6 minutes: reservation lifecycle

Reserve instead of booking. Confirm the hold through My bookings or cancel it. Explain 15-minute expiry and the background sweep. Do not wait 15 minutes during a short viva; demonstrate expiry through its isolated integration test.

For a full-train example, use the six-seat test fixture: fill six seats, add waiting groups, cancel and observe FIFO promotion. Never pretend waitlist promotion is a real railway confirmation.

### 6–8 minutes: computational thinking

Open Algorithm lab.

- Compare Dijkstra, bounded-hop DP and fastest-path branch-and-bound on Vijayawada → New Delhi.
- Change the fare budget so the constrained fastest path is infeasible.
- Try fragmented available seats in the backtracking sandbox.
- Explain why the network planner does **not** promise timetable-feasible transfers.

### 8–10 minutes: engineering evidence

Run Ruff/Mypy/Pytest or show the included actual reports. Show the cross-instance PostgreSQL race test. Compare merge sort against Python Timsort using the benchmark report. End with a limitation and a meaningful improvement plan.

## Viva questions and answer outlines

**Q: What is the primary invariant?**  
A seat identity `(train, date, class, number)` has at most one active assignment. Service transactions and a database composite primary key preserve this.

**Q: Why not rely on the “seats available” label?**  
It is a snapshot. Another buyer can book after it is rendered. Allocation must recheck under a transaction lock.

**Q: Where is decomposition visible?**  
Schemas specify inputs; services implement business rules; pure functions solve algorithmic subproblems; DB contexts own transaction boundaries; UI/API are adapters.

**Q: Where did you abstract away reality?**  
One train record is one direct route. Classes and row layout are synthetic. The graph has fare/duration edges but omits operating calendars, transfer times and partial-segment inventory.

**Q: Why greedy Dijkstra rather than arbitrary greediness?**  
Non-negative fares provide the monotonic shortest-path property. A cheapest single-edge choice without a frontier would not solve shortest path generally.

**Q: Why does DP sometimes differ from Dijkstra?**  
DP restricts the number of edges; Dijkstra is unconstrained. Compare the same objective and constraints before declaring a discrepancy a bug.

**Q: Why branch-and-bound? Is it polynomial?**  
It solves a constrained objective (fastest path under fare budget). Admissible lower bounds prune work, but worst-case simple-path enumeration remains exponential/factorial. A safety cap raises an explicit error.

**Q: Where is backtracking appropriate?**  
A six-seat row has bounded combinations. Global coach-wide combination enumeration would be unnecessarily expensive. Fallback honors feasibility rather than promising a preference.

**Q: Is your merge sort faster than Python sorted?**  
Usually not. It is inspectable teaching code. The benchmark records the comparison instead of making an unsupported optimization claim.

**Q: What are expected and amortized complexity?**  
Hash lookup has expected O(1) behavior under reasonable hash distribution, with pathological worse cases. Dynamic-array append is amortized O(1) over many appends despite occasional resizing.

**Q: Why integers for money?**  
Binary floating-point can introduce rounding surprises. The demo uses integer rupees and rational multipliers. A production application may use integer minor units or carefully configured decimal arithmetic.

**Q: What is OOP adding?**  
Replaceable fare/payment contracts, dependency composition, generic persistence and clear service responsibilities. Not every helper needs to become a class.

**Q: Which parts are functional?**  
Sorting, pricing, allocation and route computation are pure, typed functions. Their tests need no web/database side effects.

**Q: How do you prevent duplicate clicks/retries?**  
Keep the same idempotency key for a modal submission. The service hashes the command, checks it before/after locking, and a unique database constraint is the final guard. Different data with the same key is rejected.

**Q: How do you prove no double booking?**  
Tests launch concurrent requests and assert only six unique confirmed assignments for six seats. PostgreSQL is separately tested using two independent service/connection pools. Tests provide evidence, not a mathematical proof of every possible deployment.

**Q: Does async solve seat races?**  
No. Async keeps the event loop responsive. Database transactions and row locks provide resource consistency.

**Q: Why threads for I/O and processes for CPU?**  
Blocking I/O can overlap in threads; normal CPython's GIL limits pure Python CPU execution in one process. The process-pool lab is picklable and side-effect free. Small graphs may run slower in a process due to overhead.

**Q: What happens when a payment fails?**  
The injected failing provider test proves the current local simulated-payment exception rolls back booking/seats/events. Real external payment integration needs holds, an outbox/webhooks and reconciliation; a real charge cannot be rolled back by a SQL transaction.

**Q: How is the waitlist fair?**  
Oldest groups are considered first; a small new group cannot skip a larger head group. This trades throughput for FIFO fairness and can produce head-of-line blocking.

**Q: What does coverage mean?**  
Statement execution over explicitly scoped core modules. It does not prove branch completeness, accessibility, browser correctness or production performance. Browser interactions have their own tests.

**Q: How did AI help, and how did you check it?**  
Generation helped with scaffolding, service implementation, styling and tests. Actual checks found dialog scope, a CSS utility collision, typing/lint issues and a PostgreSQL sequence assumption in fixtures. Read the review log, reproduce checks and explain all remaining limitations yourself.

**Q: Can it be deployed as a real railway business?**  
Not as delivered. Official inventory integration, actual payments, timetable feasibility, security/operational controls and production migrations are out of scope.

## A live change to prove understanding

Implement a new fare-policy strategy or add a sort key, write a failing test for the desired contract, make the minimal code change, rerun quality checks, and explain why booking uniqueness/concurrency rules are unchanged.

## Before your presentation

- [ ] Read `SPECIFICATION.md` and identify omitted reality.
- [ ] Trace `create_booking`, `cancel` and `_promote` without AI help.
- [ ] Explain every algorithm's precondition and honest worst-case bound.
- [ ] Run checks on your own machine and record your own results.
- [ ] Test PostgreSQL, not only SQLite.
- [ ] Open separate traveler/admin browser sessions.
- [ ] Remove personal data from demonstration fixtures.
- [ ] State clearly that all tickets and payments are simulated.
- [ ] Be ready to make a small tested change live.
