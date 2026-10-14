# Computational Thinking and Programming — evidence map

This is a map from course outcomes to **inspectable code and executable evidence**, not a claim that a student has personally completed a viva or independently reviewed every line.

| Outcome | Evidence in the project | How to demonstrate |
|---|---|---|
| Identify a real-world problem | `docs/SPECIFICATION.md`, reservation invariants | Explain scarce-seat conflicts and retry ambiguity |
| Decompose the problem | Identity, search, fare, allocation, transaction, lifecycle, admin and testing layers | Trace a book command through the modules |
| Abstraction | `User`, `Station`, `Train`, `Inventory`, `Booking`, `SeatAssignment`, frozen graph `Edge` | Separate details needed for booking from those omitted by the teaching graph |
| Pattern recognition | Weighted paths, FIFO queues, idempotent commands and scarce resource transactions | Explain why these are recurring patterns beyond railway systems |
| Algorithm selection | `algorithms.py`, `docs/ALGORITHMS.md` | Defend a pattern for a specific subproblem, not “use all algorithms everywhere” |
| Divide-and-conquer | Stable generic `merge_sort` in train ranking | Change the key; explain split/merge recurrence |
| Dynamic programming | Bounded-hop `dynamic_route` | Compare a 2-edge and a 3-edge result on the same graph |
| Greedy | Dijkstra and deterministic seat fallback | State non-negative-cost precondition and limitations of seat preferences |
| Backtracking | Same-row contiguous allocation with pruning | Try fragmented seats in Algorithm lab |
| Branch-and-bound | Fastest simple route within a fare budget | Change budget; explain incumbent/lower-bound pruning and worst-case growth |
| Time/space complexity | `docs/ALGORITHMS.md`, `scripts/benchmark.py` | Distinguish theoretical complexity from measured microtimings |
| Amortized / expected analysis | List append, hash-table lookup/resize and deque discussion | Explain why expected O(1) is not a worst-case promise |
| Python proficiency | Pydantic/SQLAlchemy/NiceGUI modules and tests | Follow one typed input all the way to UI output |
| Data structures | Lists, sets, dicts, heaps, deque, tuples and DB indexes | Explain what would worsen if a deque were replaced with list pop(0) |
| Pythonic constructs | Comprehensions, iterator/generator `seat_labels`, `timed` decorator, context-managed DB sessions | Execute a generator lazily; inject an exception and show rollback |
| Performance-aware programming | Grouped seat query, WebP assets, bounded search, benchmark comparison | Explain remaining N+1 queries and coarse-lock limitations honestly |
| OOP / inheritance / abstraction | `FarePolicy(ABC)` → `StandardFare`; ORM base classes | Implement another fare strategy and add a unit test |
| Composition / patterns | `RailService(db, fares, payment)`, `PaymentGateway(Protocol)`, generic `Repository[T]`, unit of work | Inject `BrokenPayment`; prove no partial booking commits |
| Type hints / generics | `TypeVar`, `Generic`, `ParamSpec`, typed dataclasses and schemas | Run configured Mypy checks on seven core modules |
| Modular maintainability | UI, API, services, algorithms, DB and tests separated | Show that UI and API share business rules |
| Functional programming | Pure algorithms, higher-order key functions, immutable graph values | Explain which functions have side effects and why boundaries matter |
| Threading | NiceGUI I/O executor and `ThreadPoolExecutor` race tests | Book concurrently and inspect seat uniqueness |
| Multiprocessing | Algorithm lab `run.cpu_bound` / process pool | Run algorithms while retaining a responsive UI |
| Asynchronous programming | `asyncio.gather`, UI async handlers, expiry task | Explain cooperative coordination vs database locking |
| CPU vs I/O / GIL | `docs/ARCHITECTURE.md` | Explain why pure Python CPU loops differ from blocking SQL/native Argon2 |
| Unit / integration / E2E | Algorithm/service examples, API test client, browser workflow | Run the respective suites and inspect JUnit reports |
| Property-based testing | Hypothesis tests in `test_algorithms.py` | Generate inputs; explain shrinking and the independent brute-force oracle |
| Coverage | Actual coverage JSON + textual reports | Explain exclusion scope; coverage is not a correctness proof |
| Static checking / lint / format | Mypy config, Ruff checks and formatting | Run all three commands without disabling failing rules |
| CI/CD | `.github/workflows/ci.yml` | Explain configured quality, PostgreSQL and container build gates; no remote run/deploy is claimed |
| Containerisation | Non-root `Dockerfile`, Compose + PostgreSQL health check | Run Compose locally; explain network DB host `db` vs browser-relative paths |
| Effective AI prompting | Specification + prompt templates in `docs/AI_REVIEW.md` | Ask for a narrowly specified change and explicit invariant tests |
| Context management | Shared schemas, invariant list and module boundaries | Supply relevant contracts/tests rather than the entire repository blindly |
| AI generation / review / validation | Source + actual recorded corrections and check results | Explain the dialog nesting, utility-class and PostgreSQL fixture defects found by validation |
| Performance evaluation | Benchmark script and recorded CSV/JSON | Discuss dataset size, repeats, clock noise, memory scope and reference Timsort |
| Live demonstration | Responsive user/admin views and interactive lab | Follow the dual-session booking → admin update → cancellation demo |
| Technical defence | `docs/TECHNICAL_DEFENCE.md` | Answer the viva questions and make a tested modification live |

## Complete workflow

```text
Real-world scarce-seat problem
    ↓
Computational thinking and pattern recognition
    ↓
Decompose identity, search, pricing, allocation and lifecycle
    ↓
Define abstractions and invariants
    ↓
Select algorithms / data structures for each subproblem
    ↓
Implement typed Python services and Python-authored UI
    ↓
Use OOP strategies + pure functional algorithms
    ↓
Choose concurrency by workload and enforce DB transactions
    ↓
Run unit, property, API, PostgreSQL race and browser tests
    ↓
Lint, format, type-check; record measured performance
    ↓
Review AI-generated code and record actual defects / limitations
    ↓
Prepare CI/container configuration; deploy only after validation
    ↓
Live demo and student technical defence
```

## Suggested student extension

Add a **senior-citizen fare policy** by subclassing `FarePolicy`, pass it into `RailService`, add integer-rounding/property tests, update the fare explanation in the UI, run all checks, and explain why it should not change seat-locking behavior. This creates concrete evidence of understanding rather than just presenting a completed interface.
