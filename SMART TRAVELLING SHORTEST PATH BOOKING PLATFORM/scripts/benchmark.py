"""Reproducible in-memory measurements. No DB credentials or real tickets involved."""

import argparse
import csv
import json
import random
import statistics
import sys
import timeit
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from railora.algorithms import Edge, allocate_seats, branch_bound_route, dynamic_route, greedy_route, merge_sort  # noqa: E402


def measure(name: str, size: int, work: Callable[[], object], number: int = 10) -> dict[str, object]:
    samples = timeit.repeat(work, repeat=5, number=number)
    tracemalloc.start()
    work()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "operation": name,
        "input_size": size,
        "median_ms": round(statistics.median(samples) * 1000 / number, 5),
        "min_ms": round(min(samples) * 1000 / number, 5),
        "python_peak_kib": round(peak / 1024, 2),
        "repeats": 5,
        "runs_per_repeat": number,
    }


def graph_of_size(size: int):
    return {
        f"S{i:04d}": [Edge(f"S{j:04d}", 100 + (j - i) * 3, 5 + (j - i) * 2) for j in range(i + 1, min(size, i + 4))]
        for i in range(size)
    }


def main():
    parser = argparse.ArgumentParser(description="Measure algorithms and optional read-only database operations.")
    parser.add_argument("--database", action="store_true", help="Also time read-only operations against DATABASE_URL.")
    args = parser.parse_args()
    rng = random.Random(42)
    rows = []
    for size in [100, 1000, 5000]:
        values = [rng.randrange(100000) for _ in range(size)]
        rows.append(measure("merge_sort", size, lambda values=values: merge_sort(values, key=lambda v: v), number=5))
        rows.append(measure("python_sorted_reference", size, lambda values=values: sorted(values), number=5))
    for size in [50, 200, 500]:
        graph = graph_of_size(size)
        target = f"S{size - 1:04d}"
        rows.append(measure("dijkstra", size, lambda graph=graph, target=target: greedy_route(graph, "S0000", target)))
    graph = graph_of_size(12)
    rows.append(measure("bounded_dp_H4", 12, lambda: dynamic_route(graph, "S0000", "S0011", 4)))
    rows.append(measure("branch_bound_budget_1500", 12, lambda: branch_bound_route(graph, "S0000", "S0011", 1500)))
    rows.append(measure("seat_allocation_k6", 120, lambda: allocate_seats(list(range(1, 121)), 6)))
    database_backend = None
    if args.database:
        from sqlalchemy import select

        from railora.config import settings
        from railora.db import Database
        from railora.models import User
        from railora.services import RailService

        db = Database(settings.database_url)
        rail = RailService(db)
        database_backend = db.engine.dialect.name
        train_count = len(rail.search())
        rows.append(measure("database_train_search", train_count, lambda: rail.search("NDLS", "AGC"), number=5))
        with db.read() as session:
            admin_id = session.scalar(select(User.id).where(User.role == "admin"))
        if admin_id is not None:
            booking_count = len(rail.bookings(admin_id, admin=True))
            rows.append(
                measure("database_admin_aggregate", booking_count, lambda: rail.admin_stats(admin_id), number=3)
            )
        db.engine.dispose()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_backend": database_backend,
        "python": sys.version,
        "seed": 42,
        "scope": "Median of five repeats; algorithms run in-memory. Optional database rows are read-only, warm local service latency. Not browser/network/production or process-pool roundtrip latency.",
        "memory_scope": "tracemalloc peak Python allocation for one invocation; excludes interpreter baseline/native allocations.",
        "measurements": rows,
    }
    folder = ROOT / "reports"
    folder.mkdir(exist_ok=True)
    (folder / "performance.json").write_text(json.dumps(result, indent=2))
    with (folder / "performance.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['operation']:27s} n={row['input_size']:5d}  {row['median_ms']:9.5f} ms  {row['python_peak_kib']:9.2f} KiB"
        )


if __name__ == "__main__":
    main()
