# Executed validation and performance results

Validated on **2026-10-11**, Python **3.13.16**, PostgreSQL **17** and Chromium/Playwright. The hosted application uses PostgreSQL **CTPDB**, not SQLite.

## Test execution

| Suite | Passed | Skipped | Failures |
|---|---:|---:|---:|
| Sqlite | 48 | 5 | 0 |
| Postgres | 49 | 4 | 0 |
| Browser | 4 | 0 | 0 |

**49 PostgreSQL-backed cases and 4 separately executed browser cases passed** (53 distinct test cases). The SQLite run repeats core cases against the explicit fallback; do not add it as 48 extra distinct tests.

The PostgreSQL suite skips browser cases because no browser URL is supplied to that invocation. The browser suite is then explicitly run against the live seeded app. The SQLite suite also skips the PostgreSQL-specific cross-instance lock case.

**PostgreSQL core statement coverage: 98.49%** (846/859 statements). Algorithms, API, models, schemas, config and ticket generation each reached 100% statement coverage in that run.

Coverage intentionally excludes Python UI components and synthetic seeding; browser tests exercise those flows separately. This is not a full-UI coverage percentage, branch-coverage claim, formal proof or accessibility/security audit.

### Additional UI inspection

Desktop 1440px and mobile 390px layouts were inspected. Additional smoke checks passed for the `/` quick-search shortcut, route planner, saved/registration pages, admin directory/register/audit feed, add-train modal and train pause/resume. No uncaught browser JavaScript errors were observed in these checks. See `reports/ui-smoke.json`.

### Quality gates

- Ruff lint: passed (`reports/lint.txt`).
- Ruff formatting check: passed (`reports/format.txt`).
- Mypy: passed on **seven core modules** (`reports/typecheck.txt`).
- Python compilation: passed.
- CI and Docker Compose YAML: parsed and structurally checked.

A Starlette/httpx TestClient deprecation warning is retained in the test logs. It did not prevent any test from running or passing; it is a dependency-maintenance note, not a suppressed error.

## Measured performance

Seeded/random inputs use seed 42. Timings are the median per call over **five repeats**. Sort tests use five calls per repeat; graph/seat tests use ten. Database timings are read-only, warm local service calls (five search / three admin calls per repeat). They exclude the browser, network proxy and process-pool transport. Peak KiB is `tracemalloc` Python allocation for one call, not whole-system or PostgreSQL server memory.

| Operation | Input size | Median ms | Python peak KiB |
|---|---:|---:|---:|
| `merge_sort` | 100 | 0.14546 | 4.00 |
| `python_sorted_reference` | 100 | 0.00167 | 0.85 |
| `merge_sort` | 1000 | 1.97095 | 33.05 |
| `python_sorted_reference` | 1000 | 0.03830 | 11.75 |
| `merge_sort` | 5000 | 12.50938 | 159.10 |
| `python_sorted_reference` | 5000 | 0.58121 | 58.51 |
| `dijkstra` | 50 | 0.07181 | 5.01 |
| `dijkstra` | 200 | 0.26504 | 21.20 |
| `dijkstra` | 500 | 0.76966 | 43.72 |
| `bounded_dp_H4` | 12 | 0.02453 | 1.08 |
| `branch_bound_budget_1500` | 12 | 0.06641 | 2.77 |
| `seat_allocation_k6` | 120 | 0.01811 | 11.33 |
| `database_train_search` | 15 | 3.54711 | 50.08 |
| `database_admin_aggregate` | 46 | 89.62213 | 309.77 |

### Interpretation

- Python built-in `sorted()` is substantially faster than the inspectable teaching merge sort. Its native Timsort is a sensible production replacement.
- Dijkstra timings grow with graph size; tiny single-run lab timings are noisy and do not establish a general speed ranking.
- This small branch-and-bound input prunes well; it does not contradict the exponential/factorial worst-case path count.
- Admin aggregation is comparatively expensive because the current demo serializes the full register with additional per-booking queries. SQL-side pagination, joined loading and indexed aggregates are the next measured optimization target.
- Process-pool overhead can exceed tiny graph computation time; concurrency in the lab is a correct mechanism demonstration, not a claimed speedup.

## Reproduce

```bash
ruff check .
ruff format --check .
mypy
TEST_DATABASE_URL='postgresql+psycopg://postgres:root@localhost:5432/CTPDB_test' pytest --cov
RAILORA_E2E_URL=http://localhost:8080 pytest tests/test_e2e.py -v
python scripts/benchmark.py --database
```

Use isolated `*_test` databases and a disposable seeded app. Browser tests create and cancel their own demo booking. Assistant-created exploratory/browser records were cleaned from the hosted demo after validation; genuine user-created records are not targeted by that cleanup.

## Included but not executed here

- Docker image build and Compose launch (Docker is not installed in the delivery sandbox).
- Remote GitHub Actions execution; the quality/browser/container jobs are configuration, not a reported remote run.
- Real payment/railway integration, production deployment, external email/SMS, penetration testing, full accessibility audit, load testing at national railway scale.

The app is an academic demonstration. See the specification, architecture and AI review for deliberate limits and remaining work.
