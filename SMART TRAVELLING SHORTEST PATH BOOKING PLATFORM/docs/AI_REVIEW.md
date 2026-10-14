# AI-assisted software engineering: review record

## Role of AI assistance

This project was produced with AI-assisted specification interpretation, Python generation, UI design, test generation and tool-driven validation. AI output was treated as a draft and subjected to actual execution, browser inspection, property tests and PostgreSQL integration tests.

This document does **not** claim an independent human security audit, a student's personal authorship, a passed technical viva, a remotely executed CI workflow or a deployed production railway integration. A student must perform their own review, reproduce the checks and understand the implementation.

## Specification-first context

Before implementing transactions, the design separated identity, search, pricing, group allocation, booking lifecycle and administrative observation. Core invariants were identified from the user requirements: unique seat ownership, atomic commit, idempotent retries, FIFO promotion, ownership and role checks, exact money and explicit simulated payments.

The shared Pydantic schemas and service contracts keep frontend and backend context consistent. Documentation records those contracts so subsequent changes can be reviewed against a stable specification.

## Actual issues identified and corrected

| Finding | Validation method | Correction |
|---|---|---|
| Booking succeeded but its success dialog was not visible because it was nested inside the dialog that had just closed | Browser workflow + database/API verification | Root the new dialog in the client content outside the closed booking modal |
| Admin reservation rows collapsed into a vertical table-like layout; a Tailwind utility name conflicted with a custom class | Desktop screenshot inspection + computed-style check | Rename `table-row` to `data-row`; enforce grid layout |
| NiceGUI dialog card flex defaults caused the header/footer to shrink instead of spanning the booking modal | Browser screenshot inspection | Make custom modal cards block layout and span the intended width |
| Initial UI session storage path's parent did not exist | Server traceback on first run | Create the full storage directory with `parents=True` before importing/running NiceGUI |
| A sandbox PostgreSQL cluster initialized with SQL_ASCII returned byte strings during dialect discovery | Actual PostgreSQL connection failure | Create the project/test databases with UTF-8; the provided PostgreSQL container uses its normal UTF-8 initialization |
| Test fixtures with manually specified integer IDs did not advance PostgreSQL sequences, causing registration/train insertion collisions unseen on SQLite | First PostgreSQL suite: four failing tests | Let the database allocate fixture IDs; rerun the full PostgreSQL suite successfully |
| Argon2's typed verification return was inferred as literal `True`, conflicting with the exception-path `False` assignment | Mypy | Annotate the local verification result as `bool` |
| Backtracking closure referenced a loop variable, creating a lint warning and unnecessarily implicit binding | Ruff | Explicitly bind the row used by the recursive search |
| Dijkstra originally copied a complete path tuple into each frontier entry, adding avoidable work and weakening the stated complexity | Algorithm review | Store predecessors and reconstruct the final path once |
| Input length checks alone accepted whitespace names; train duration could contradict displayed times | Critical schema review + added regression tests | Strip/check names and validate duration modulo 24 hours against departure/arrival |
| UTC timestamps were initially bucketed by UTC date while the dashboard's days were Indian local dates | Timezone review + regression test using 20:00 UTC | Convert booking creation timestamps into Asia/Kolkata calendar dates for chart aggregation |
| Mobile date/class fields left an unnecessary empty grid row | Mobile screenshot inspection | Correct the responsive direct-child selectors |
| A displayed keyboard shortcut had no handler | UI review | Add the actual `/` quick-search keyboard handler instead of a decorative command shortcut |

All final claims should be checked against `docs/VALIDATION.md` and the included executed reports. Failed intermediate results were not presented as final passes.

## Reusable prompting templates — examples, not fabricated conversation logs

### Specify before generating

> Implement a direct-route railway booking command using the provided BookingInput schema. Preserve seat uniqueness, atomic booking/seat/event commit, idempotency and FIFO waitlist fairness. PostgreSQL must enforce cross-process concurrency. Do not use a Python mutex as the only lock. Describe the lock order and failure behavior before producing code.

### Manage context narrowly

> Here are schemas.py, the create_booking contract, the seat-assignment primary key and the relevant tests. Add a fare-policy strategy without changing allocation, authorization or transaction boundaries. State which files need modification and which invariants must remain true.

### Review adversarially

> Review this reservation lifecycle for duplicate clicks, expired holds, rollback on provider failure, full trains, large waitlisted groups and two simultaneous buyers. Identify concrete counterexamples. Do not assume that an async function prevents shared-resource races.

### Generate falsifiable tests

> Write independent property tests: allocation only returns available unique seats; merge sort agrees with Python sorted and preserves tie order; branch-and-bound matches brute-force enumeration on small graphs. Include failing edge cases rather than only the happy path.

### Improve after measurement

> The included benchmark shows Python sorted is faster than the teaching merge sort, and admin serialization has per-booking queries. Explain why, propose a bounded improvement, and do not claim a production speedup without a repeatable measurement.

## Context and responsibility rules

- Supply the existing specification, schemas and relevant tests before requesting a change.
- Use synthetic passengers and development credentials in examples. Never provide real secrets, card data, IDs or personal booking records to an AI prompt.
- Keep model-generated code changes small enough to inspect.
- Do not silence a failing test or loosen an invariant merely to get a green run.
- Check external dependencies and image rights; web search is not a license.
- Record actual commands, versions, report scope and limits. Do not invent coverage, benchmarks or external integrations.
- Ask a human reviewer to evaluate production authentication, authorization, payments, migrations and operational safety before any real deployment.

## Student review checklist

- [ ] Read and explain every public service method without relying on generated summaries.
- [ ] Reproduce the reported tests on your own PostgreSQL installation.
- [ ] Inspect the race tests and describe what they do and do not prove.
- [ ] Review the schema and money rules; add one meaningful edge-case test.
- [ ] Explain the abstraction gap between a graph path and a timetable-feasible railway trip.
- [ ] Compare the measured sort implementations and identify a bottleneck.
- [ ] Implement one small extension and defend its effect on invariants.
- [ ] Clearly acknowledge AI assistance according to your institution's rules.
