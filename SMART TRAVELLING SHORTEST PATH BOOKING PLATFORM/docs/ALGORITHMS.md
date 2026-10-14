# Algorithm selection, data structures and complexity

## What belongs in the actual booking path?

Use small, predictable operations for booking. Do not run branch-and-bound over the railway network while holding a seat lock. Graph route algorithms belong to the **interactive educational planner/lab**, while merge sort and seat allocation are used by real search/booking code.

Let `n` be input items or available seat count; `k≤6` be group size; `V,E` be graph vertices/edges; `H` be the DP hop bound.

| Pattern / routine | Purpose | Time | Auxiliary space | Important qualification |
|---|---|---|---|---|
| Divide-and-conquer `merge_sort` | Stable search ranking | O(n log n) | O(n) peak + O(log n) stack | Slices/merges allocate a cumulative O(n log n) elements; peak is O(n). Key extraction is assumed O(1). |
| Greedy Dijkstra `greedy_route` | Cheapest non-negative network path | O((V+E) log(V+E)) with duplicate heap entries | O(V+E) | For simple graphs this is the usual O((V+E) log V) bound. Predecessors avoid copying full paths on every relaxation. Final path reconstruction is O(V). |
| DP `dynamic_route` | Cheapest route with ≤H edges | O(H·(V+E)) relax/copy work plus up to O(H²·E) path-tuple copying | O(H·V) with stored path tuples | Only previous/current layers are retained. This teaching implementation stores paths rather than an optimized predecessor-layer table. |
| Bounded backtracking `allocate_seats` | Prefer contiguous same-row group | O(n log n + n·2⁶) | O(n) plus depth ≤6 | Rows are six seats; a bounded combination search cannot explode with coach size. With fixed width, sorting dominates asymptotically. |
| Greedy seat fallback | Earliest/window-preferred free seats | O(n log n) including sorting | O(n) | It guarantees availability/uniqueness, not that every preference is satisfied. |
| Branch-and-bound `branch_bound_route` | Fastest simple path within a fare budget | Exponential/factorial path enumeration in the worst case; lower-bound preprocessing O(V·E) | O(V) recursion/path depth plus graph/lower-bound storage | Each branch also sorts outgoing edges and copies a path prefix. The cap of 20,000 states raises an error rather than claiming unfinished work is optimal. |
| Pure integer `fare_quote` | Exact price and service fee | O(1) | O(1) | Integer rupees; rational class multipliers round upward explicitly. |
| `seat_labels` generator | Format assigned seats lazily | O(k) to consume | O(1) generator state, excluding output list | Generator creation alone does not do all formatting work. |

Complexities above describe in-memory algorithms. Database query/locking latency and browser rendering are separate costs.

## 1. Divide and conquer

`merge_sort(items, key)` splits the list, recursively sorts both halves, then merges them. The left item wins equal-key ties, preserving stability. Train sorting choices pass different functions without duplicating the algorithm.

**Why not always use this in production?** Python's built-in Timsort is implemented in optimized native code and is typically faster and more adaptive. A custom stable merge sort is included to make the course pattern inspectable. `scripts/benchmark.py` measures both; no claim that educational code beats `sorted()` is made.

## 2. Greedy frontier and pattern recognition

Treat each station as a node and a sample service as a directed edge weighted by base fare. For non-negative weights, settling the minimum-cost frontier gives Dijkstra's correctness argument. `heapq` stores a min-priority frontier; a dictionary stores best-known distances and predecessors.

Reject negative fare/duration weights explicitly. Train edge fares are base fares only; fees and class multipliers are not part of this illustrative network graph. The graph does not represent timetable-feasible connections.

## 3. Dynamic programming

State: best known cost/path to a node using at most the current number of edges.

Recurrence:

```text
D[h][v] = min(D[h-1][v], min over (u→v) of D[h-1][u] + fare(u,v))
```

Reuse the prior layer, not newly written current-layer states. This prevents unintentionally allowing unlimited edges in one layer. A bounded-hop result can differ legitimately from unconstrained Dijkstra. The lab fixes `H=4`, and property tests compare both where `V-1=4` suffices for a shortest simple path.

## 4. Backtracking with a realistic bound

Within each six-seat row, grow a candidate contiguous group and prune a prefix that cannot possibly reach the requested size. Return the first feasible row. If no contiguous same-row group exists, choose deterministic free seats rather than failing a satisfiable reservation.

The important constraints are **free, unique, within inventory**. “Together” and “window” are preferences. They are not guarantees about a real railway coach or seat selection by the traveler.

A global unconstrained combination search would have O(C(n,k)) candidates. It is deliberately **not used** here.

## 5. Branch and bound

Optimization objective: minimize total minutes over simple directed paths while respecting a base-fare budget.

Compute an admissible shortest remaining-time lower bound with reverse relaxations. A branch can be pruned when:

- its accumulated fare exceeds the budget, or
- accumulated minutes + optimistic remaining minutes cannot beat the incumbent.

Positive/non-negative costs and visited-path checks prevent cycling through a path. A lower bound helps average cases but does not remove exponential worst-case growth. The implementation is appropriate for the tiny teaching graph, not a production national-network optimizer.

## Data-structure decisions

| Structure | Actual use | Complexity / rationale |
|---|---|---|
| List | Passenger records and ordered candidates | Index O(1), append amortized O(1), middle deletion O(n) |
| Set | Taken seats and chosen-seat membership | Expected O(1) lookup/insertion; pathological worst O(n) |
| Dictionary | Stations, graph adjacency, distances, class multipliers | Expected O(1) lookup; rehash growth means amortized insertion behavior |
| `heapq` | Dijkstra frontier | Push/pop O(log m), min peek O(1) |
| `deque` | FIFO promotion traversal | Append/popleft O(1), avoiding list pop(0) shifting |
| Tuple / frozen dataclass | Immutable route outputs and edge values | Explicit immutable value semantics; tuple path copies are not free |
| Composite DB primary key | Seat and inventory identity | Enforces uniqueness even across application processes |
| DB indexes | Route, date, status and waitlist filtering | B-tree lookup typically O(log N + result size); planner/I/O/cache behavior matters |

Expected and amortized bounds are not interchangeable with worst-case guarantees. Likewise, a transaction waiting for a lock may be slow despite an O(n) seat computation.

## Performance-aware engineering

- Query occupied seats in one grouped SQL query for search results, rather than one query per seat.
- Keep transactions short; the payment provider is explicitly a local simulation. A real external payment request should not be added directly inside this locked transaction.
- Limit group size, coach capacity and branch-and-bound states.
- Reconstruct Dijkstra paths from predecessors rather than retaining full frontier paths.
- Cache web photography locally and optimize images to WebP.
- Generate PDF bytes only when the traveler requests a ticket.
- Paginate the admin reservation register (12 rows per UI page).

### Current scaling limitation

Reservation display serialization currently performs additional per-booking ORM queries and materializes the reservation list before UI pagination. This is acceptable for the small demo, but **not an efficient large-scale register**. Production work should add SQL-side pagination, joined/batched loading and indexed aggregates. The coarse train lock also limits throughput across dates/classes. These limitations are part of the technical defence, not hidden behind generic “scalable” claims.

## Verification methods

- Merge sort properties: same output and stability as Python `sorted()`.
- Allocation properties: no duplicates; all output seats were free; result count matches feasible inventory.
- Fare properties: exact integers and linear passenger scaling.
- Small-graph properties: Dijkstra equals DP when sufficient hops are allowed; branch-and-bound agrees with independent brute-force enumeration.
- Concurrency tests: many requests for six seats result in exactly six confirmed seat owners; identical retries produce one PNR.
- Real PostgreSQL test: two independent service/database instances contend on the same inventory.

Measured results are recorded in `reports/performance.json` and described in `docs/VALIDATION.md`.
