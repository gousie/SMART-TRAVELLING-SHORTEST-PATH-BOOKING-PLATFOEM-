"""Pure, typed algorithms used by booking, search and the network teaching lab.

Do not use every algorithm everywhere: each pattern addresses a distinct subproblem.
The route lab is a simplified station graph, NOT a timetable/connection booking engine.
"""

import logging
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from functools import wraps
from heapq import heappop, heappush
from itertools import count
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger(__name__)


def timed(function: Callable[P, R]) -> Callable[P, R]:
    """A decorator preserving signature, return type and metadata."""

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            logger.debug("%s completed in %.3f ms", function.__name__, (perf_counter() - start) * 1000)

    return wrapped


def merge_sort(items: Sequence[T], key: Callable[[T], Any]) -> list[T]:
    """Stable divide-and-conquer sort: O(n log n) time; O(n) auxiliary space."""
    if len(items) <= 1:
        return list(items)
    midpoint = len(items) // 2
    left = merge_sort(items[:midpoint], key)
    right = merge_sort(items[midpoint:], key)
    result: list[T] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    return result + left[i:] + right[j:]


def seat_labels(seats: Iterable[int]) -> Iterator[str]:
    """Lazy generator: C1-01 through C1-36, C2-01 onwards."""
    for seat in seats:
        yield f"C{(seat - 1) // 36 + 1}-{(seat - 1) % 36 + 1:02d}"


def allocate_seats(available: Sequence[int], size: int, preference: str = "together") -> list[int]:
    """Bounded backtracking finds a same-row group, then a deterministic greedy fallback.

    Window requests prefer edge seats. 'Together' is a preference, not a guarantee.
    Search considers at most six places in each coach row, so it cannot explode with
    large inventory. Including sorting: O(n log n + n * 2^6) time, O(n) space.
    With fixed row width and k<=6, the sort dominates asymptotically.
    """
    if not 1 <= size <= 6:
        raise ValueError("Passenger count must be between one and six.")
    ordered = sorted(set(available))
    if len(ordered) < size:
        return []
    if preference == "window":
        ordered.sort(key=lambda s: (s % 6 not in (0, 1), s))
        return ordered[:size]
    if preference == "together":
        rows: dict[int, list[int]] = defaultdict(list)
        for seat in ordered:
            rows[(seat - 1) // 6].append(seat)
        for row in rows.values():

            def search(index: int, chosen: list[int], row: list[int] = row) -> list[int] | None:
                if len(chosen) == size:
                    return chosen.copy()
                if len(row) - index < size - len(chosen):
                    return None
                for j in range(index, len(row)):
                    if not chosen or row[j] == chosen[-1] + 1:
                        found = search(j + 1, chosen + [row[j]])
                        if found is not None:
                            return found
                return None

            found = search(0, [])
            if found is not None:
                return found
    return ordered[:size]


def fare_quote(base: int, travel_class: str, passengers: int) -> dict[str, int]:
    """Integer-money pure function: no binary floating-point rounding errors."""
    multipliers = {"CC": (1, 1), "3A": (6, 5), "SL": (3, 5)}
    if base <= 0 or passengers < 1 or travel_class not in multipliers:
        raise ValueError("Invalid fare inputs.")
    numerator, denominator = multipliers[travel_class]
    ticket = (base * numerator + denominator - 1) // denominator
    subtotal = ticket * passengers
    fee = 20 * passengers
    return {"ticket": ticket, "subtotal": subtotal, "fee": fee, "total": subtotal + fee}


@dataclass(frozen=True)
class Edge:
    destination: str
    fare: int
    minutes: int
    train_number: str = ""


Graph = dict[str, list[Edge]]


@dataclass(frozen=True)
class RouteResult:
    path: tuple[str, ...]
    cost: int
    visited: int = 0
    pruned: int = 0


def _validate_graph(graph: Graph) -> None:
    if any(edge.fare < 0 or edge.minutes < 0 for edges in graph.values() for edge in edges):
        raise ValueError("Route costs must be non-negative.")


def greedy_route(graph: Graph, origin: str, destination: str) -> RouteResult | None:
    """Dijkstra: a greedy frontier with a min heap; O((V+E) log V)."""
    _validate_graph(graph)
    serial = count()
    frontier: list[tuple[int, int, str]] = [(0, next(serial), origin)]
    best = {origin: 0}
    predecessor: dict[str, str] = {}
    visited = 0
    while frontier:
        cost, _, node = heappop(frontier)
        if cost != best[node]:
            continue
        visited += 1
        if node == destination:
            path = [destination]
            while path[-1] != origin:
                path.append(predecessor[path[-1]])
            return RouteResult(tuple(reversed(path)), cost, visited)
        for edge in graph.get(node, []):
            candidate = cost + edge.fare
            if candidate < best.get(edge.destination, float("inf")):
                best[edge.destination] = candidate
                predecessor[edge.destination] = node
                heappush(frontier, (candidate, next(serial), edge.destination))
    return None


def dynamic_route(graph: Graph, origin: str, destination: str, max_hops: int = 4) -> RouteResult | None:
    """Bounded-edge Bellman DP: O(H*E) relaxations, O(H*V) states + stored paths.

    Bounded hops are a real constraint, so this may differ from unbounded Dijkstra.
    Full path tuples incur an extra O(H) copy factor in this teaching implementation.
    """
    _validate_graph(graph)
    if max_hops < 0:
        raise ValueError("max_hops must be non-negative.")
    previous: dict[str, tuple[int, tuple[str, ...]]] = {origin: (0, (origin,))}
    result = RouteResult((origin,), 0) if origin == destination else None
    visits = 0
    for _ in range(max_hops):
        current = previous.copy()
        for node, (cost, path) in previous.items():
            for edge in graph.get(node, []):
                visits += 1
                candidate = cost + edge.fare
                if candidate < current.get(edge.destination, (float("inf"), ()))[0]:
                    current[edge.destination] = (candidate, path + (edge.destination,))
        previous = current
        if destination in current:
            price, path = current[destination]
            result = RouteResult(path, price, visits)
    return result


def branch_bound_route(
    graph: Graph, origin: str, destination: str, budget: int, max_states: int = 20000
) -> RouteResult | None:
    """Minimise journey minutes under a fare budget over simple paths.

    A remaining-time lower bound prunes branches; exponential worst case.
    A safety cap raises an error instead of pretending an unfinished search is optimal.
    """
    _validate_graph(graph)
    if budget < 0:
        return None
    nodes = {origin, destination, *graph.keys(), *(e.destination for es in graph.values() for e in es)}
    lower = dict.fromkeys(nodes, float("inf"))
    lower[destination] = 0
    # Reverse Bellman relaxation for admissible shortest remaining-time lower bounds.
    for _ in range(len(nodes) - 1):
        for node, edges in graph.items():
            for edge in edges:
                lower[node] = min(lower[node], edge.minutes + lower[edge.destination])
    best_time = float("inf")
    best_path: tuple[str, ...] | None = None
    visited = pruned = 0

    def walk(node: str, path: tuple[str, ...], fare: int, minutes: int) -> None:
        nonlocal best_time, best_path, visited, pruned
        visited += 1
        if visited > max_states:
            raise ValueError("Search safety limit reached; reduce graph size.")
        if fare > budget or minutes + lower[node] >= best_time:
            pruned += 1
            return
        if node == destination:
            best_time, best_path = minutes, path
            return
        for edge in sorted(graph.get(node, []), key=lambda e: e.minutes + lower[e.destination]):
            if edge.destination not in path:
                walk(edge.destination, path + (edge.destination,), fare + edge.fare, minutes + edge.minutes)

    walk(origin, (origin,), 0, 0)
    return RouteResult(best_path, int(best_time), visited, pruned) if best_path else None


def benchmark_lab(graph: Graph, origin: str, destination: str, budget: int) -> list[dict[str, Any]]:
    """Picklable CPU-bound function; the UI runs this in NiceGUI's process pool."""
    jobs: list[tuple[str, Callable[[], RouteResult | None]]] = [
        ("Greedy · Dijkstra", lambda: greedy_route(graph, origin, destination)),
        ("Dynamic programming · ≤4 edges", lambda: dynamic_route(graph, origin, destination, 4)),
        ("Branch & bound · fastest within budget", lambda: branch_bound_route(graph, origin, destination, budget)),
    ]
    results = []
    for name, job in jobs:
        start = perf_counter()
        result = job()
        elapsed = (perf_counter() - start) * 1000
        results.append(
            {
                "algorithm": name,
                "path": list(result.path) if result else [],
                "cost": result.cost if result else None,
                "visited": result.visited if result else 0,
                "pruned": result.pruned if result else 0,
                "ms": round(elapsed, 4),
            }
        )
    return results
