"""Example-based and property-based proofs of important algorithm invariants."""

from functools import reduce

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from railora.algorithms import (
    Edge,
    allocate_seats,
    benchmark_lab,
    branch_bound_route,
    dynamic_route,
    fare_quote,
    greedy_route,
    merge_sort,
    seat_labels,
    timed,
)


@given(st.lists(st.integers(-1000, 1000), max_size=100))
def test_merge_sort_matches_python(values):
    assert merge_sort(values, key=lambda x: x) == sorted(values)


@given(st.lists(st.integers(0, 10), max_size=100))
def test_merge_sort_is_stable(values):
    indexed = list(enumerate(values))
    assert merge_sort(indexed, key=lambda item: item[1]) == sorted(indexed, key=lambda item: item[1])


@given(st.lists(st.integers(1, 120), max_size=120), st.integers(1, 6), st.sampled_from(["any", "window", "together"]))
def test_allocated_seats_are_unique_available_and_bounded(available, size, preference):
    result = allocate_seats(available, size, preference)
    assert len(result) == (size if len(set(available)) >= size else 0)
    assert len(result) == len(set(result))
    assert set(result) <= set(available)


@pytest.mark.parametrize(
    ("available", "size", "expected"),
    [
        ([1, 3, 4, 5, 6], 3, [3, 4, 5]),
        ([1, 3, 5, 7], 3, [1, 3, 5]),
        ([1, 2], 3, []),
        ([], 1, []),
        ([6, 7, 8, 9], 3, [7, 8, 9]),
    ],
)
def test_together_row_backtracking(available, size, expected):
    assert allocate_seats(available, size, "together") == expected


def test_window_preference_and_generator():
    assert allocate_seats([2, 3, 6, 7], 2, "window") == [6, 7]
    generator = seat_labels([1, 36, 37, 72])
    assert iter(generator) is generator
    assert list(generator) == ["C1-01", "C1-36", "C2-01", "C2-36"]


@pytest.mark.parametrize("size", [0, 7, -1])
def test_invalid_group_size(size):
    with pytest.raises(ValueError):
        allocate_seats([1, 2], size)


@given(st.integers(1, 15000), st.sampled_from(["CC", "3A", "SL"]), st.integers(1, 6))
def test_fare_is_integer_money_and_scales(base, travel_class, size):
    quote = fare_quote(base, travel_class, size)
    assert all(isinstance(value, int) for value in quote.values())
    assert quote["total"] == quote["ticket"] * size + 20 * size
    assert quote["total"] >= quote["subtotal"] > 0


@pytest.mark.parametrize(("base", "cls", "size"), [(0, "CC", 1), (100, "invalid", 1), (100, "CC", 0)])
def test_invalid_fare(base, cls, size):
    with pytest.raises(ValueError):
        fare_quote(base, cls, size)


def example_graph():
    return {
        "A": [Edge("B", 100, 90), Edge("C", 250, 30)],
        "B": [Edge("C", 100, 40), Edge("D", 500, 20)],
        "C": [Edge("D", 100, 40)],
    }


def test_greedy_and_dynamic_example():
    graph = example_graph()
    assert greedy_route(graph, "A", "D").cost == 300
    assert greedy_route(graph, "A", "D").path == ("A", "B", "C", "D")
    assert dynamic_route(graph, "A", "D", 2).cost == 350
    assert dynamic_route(graph, "A", "D", 3).cost == 300
    assert dynamic_route(graph, "A", "D", 0) is None
    assert greedy_route(graph, "D", "A") is None
    assert dynamic_route(graph, "D", "A", 3) is None


def test_budget_changes_fastest_feasible_path():
    graph = example_graph()
    assert branch_bound_route(graph, "A", "D", 350).path == ("A", "C", "D")
    assert branch_bound_route(graph, "A", "D", 300).cost == 170
    assert branch_bound_route(graph, "A", "D", 299) is None
    assert branch_bound_route(graph, "A", "D", -1) is None
    assert branch_bound_route(graph, "A", "A", 10).cost == 0
    with pytest.raises(ValueError):
        branch_bound_route(graph, "A", "D", 1000, max_states=0)


@settings(max_examples=80)
@given(st.lists(st.tuples(st.integers(0, 4), st.integers(0, 4), st.integers(0, 500), st.integers(1, 100)), max_size=14))
def test_nonnegative_dijkstra_matches_bounded_dp_and_branch_bruteforce(edges):
    graph = {str(i): [] for i in range(5)}
    for a, b, fare, minutes in edges:
        if a != b:
            graph[str(a)].append(Edge(str(b), fare, minutes))
    greedy = greedy_route(graph, "0", "4")
    dynamic = dynamic_route(graph, "0", "4", 4)
    assert (greedy.cost if greedy else None) == (dynamic.cost if dynamic else None)
    candidates = []

    def brute(node, path, fare, minutes):
        if fare > 500:
            return
        if node == "4":
            candidates.append(minutes)
            return
        for edge in graph[node]:
            if edge.destination not in path:
                brute(edge.destination, path + [edge.destination], fare + edge.fare, minutes + edge.minutes)

    brute("0", ["0"], 0, 0)
    result = branch_bound_route(graph, "0", "4", 500)
    assert (result.cost if result else None) == (min(candidates) if candidates else None)


def test_negative_edges_rejected_and_invalid_hop_limit():
    graph = {"A": [Edge("B", -1, 5)]}
    for fn in [greedy_route, dynamic_route]:
        with pytest.raises(ValueError):
            fn(graph, "A", "B")
    with pytest.raises(ValueError):
        branch_bound_route(graph, "A", "B", 100)
    with pytest.raises(ValueError):
        dynamic_route({}, "A", "B", -1)
    assert dynamic_route({}, "A", "A", 0).cost == 0


def test_timing_decorator_preserves_result_and_metadata():
    @timed
    def add(a: int, b: int) -> int:
        """Add numbers."""
        return a + b

    assert add(2, 3) == 5
    assert add.__name__ == "add"
    assert add.__doc__ == "Add numbers."
    assert reduce(add, [1, 2, 3]) == 6


def test_lab_benchmark_returns_measured_outputs():
    results = benchmark_lab(example_graph(), "A", "D", 350)
    assert len(results) == 3
    assert results[0]["cost"] == 300
    assert all(r["ms"] >= 0 for r in results)
    assert results[-1]["cost"] == 70
    assert benchmark_lab({}, "A", "B", 100)[0]["path"] == []
