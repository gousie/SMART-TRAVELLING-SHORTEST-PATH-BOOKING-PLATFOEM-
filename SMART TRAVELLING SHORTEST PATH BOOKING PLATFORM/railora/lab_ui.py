"""Interactive computational-thinking demonstration, not a fabricated course checklist."""

from nicegui import run, ui

from railora.algorithms import allocate_seats, benchmark_lab, greedy_route, seat_labels
from railora.config import ROOT
from railora.web_components import button, icon, money, network_svg, page_heading, section_title


class LabUI:
    def __init__(self, web):
        self.web = web

    async def network(self):
        user = await self.web.profile()
        if not user:
            return
        trains = await run.io_bound(self.web.rail.search)
        graph = await run.io_bound(self.web.rail.graph)
        chosen = {"path": []}
        with self.web.shell(user, "/routes", "Route explorer"):
            page_heading(
                "Let curiosity choose the destination",
                "A world of connections.",
                "Discover the station network and see how a route-finding algorithm thinks.",
            )
            with ui.element("div").classes("network-layout"):
                with ui.element("div").classes("card map-card"):
                    section_title(
                        "The Railora network",
                        f"{len(self.web.stations)} stations · {len(trains)} active sample services",
                    )

                    @ui.refreshable
                    def map_view():
                        ui.html(network_svg(self.web.stations, trains, chosen["path"])).classes("network-map")

                    map_view()
                    ui.html(
                        '<div class="map-legend"><div><i class="legend-dot"></i> Sample station</div><div><i style="width:20px;height:2px;background:#c8c4da"></i> Direct service</div></div>'
                    )
                with ui.element("div").classes("card network-control"):
                    ui.label("Follow the rails").classes("section-title")
                    ui.label("Cheapest network path · Greedy Dijkstra").classes("small muted")
                    origin = ui.select(self.web.station_options, label="Starting station", value="BZA").props(
                        "outlined dense hide-bottom-space"
                    )
                    destination = ui.select(self.web.station_options, label="Destination", value="NDLS").props(
                        "outlined dense hide-bottom-space"
                    )
                    output = ui.element("div").classes("wide")

                    async def plan():
                        plan_button.disable()
                        try:
                            result = await run.io_bound(greedy_route, graph, origin.value, destination.value)
                            output.clear()
                            with output:
                                if result:
                                    chosen["path"] = list(result.path)
                                    map_view.refresh()
                                    ui.label(" → ".join(self.web.city(p) for p in result.path)).classes("lab-path")
                                    ui.label(f"{money(result.cost)} · sum of base fares, before fees").classes(
                                        "small muted"
                                    ).style("margin-top:8px")
                                    ui.label(
                                        f"{max(0, len(result.path) - 1)} edges · {result.visited} nodes settled"
                                    ).classes("tiny muted").style("margin-top:5px")
                                    if len(result.path) == 2:
                                        button(
                                            "View direct trains",
                                            lambda: self.web.choose_route(origin.value, destination.value),
                                            "text",
                                            "arrow",
                                        )
                                else:
                                    chosen["path"] = []
                                    map_view.refresh()
                                    ui.label(
                                        "No directed path connects these stations. Try Vijayawada → New Delhi or New Delhi → Agra."
                                    ).classes("small muted")
                        finally:
                            plan_button.enable()

                    plan_button = button("Find a network path", plan, "primary", "map").classes("wide")
                    with ui.element("div").classes("notice"):
                        ui.label(
                            "Teaching visualisation only. This graph does not check transfer times, operating days or through-ticket availability. Multi-train paths cannot be booked as an itinerary here."
                        )
            with ui.element("div").classes("lab-pattern-grid"):
                for title, text, symbol in [
                    (
                        "Recognise the pattern",
                        "Stations are nodes. Direct train services are edges. Non-negative fares make this a weighted shortest-path problem.",
                        "map",
                    ),
                    (
                        "Abstract the details",
                        "The teaching graph keeps station codes, fare weights and durations, leaving detailed timetables to a future connection-aware planner.",
                        "code",
                    ),
                    (
                        "Choose the right algorithm",
                        "Dijkstra expands the lowest-cost frontier first. A min heap and a distance dictionary avoid revisiting costly paths.",
                        "chart",
                    ),
                ]:
                    with ui.element("div").classes("pattern-card"):
                        with ui.element("div").classes("stat-icon purple"):
                            icon(symbol)
                        ui.label(title).classes("pattern-title")
                        ui.label(text).classes("pattern-description")

    async def laboratory(self):
        user = await self.web.profile()
        if not user:
            return
        graph = await run.io_bound(self.web.rail.graph)
        with self.web.shell(user, "/lab", "Algorithm lab"):
            page_heading(
                "Computational thinking, made visible",
                "Behind every smooth journey.",
                "Explore the algorithms, abstractions and engineering that make Railora work.",
            )
            with ui.element("div").classes("workflow"):
                for i, label in enumerate(
                    [
                        "Real-world problem",
                        "Decomposition",
                        "Abstraction",
                        "Algorithms",
                        "Python & OOP",
                        "Concurrency",
                        "Test & review",
                        "Live demo",
                    ],
                    1,
                ):
                    with ui.element("div").classes("workflow-step"):
                        ui.label(str(i)).classes("workflow-number")
                        ui.label(label)
            with ui.element("div").classes("network-layout"):
                with ui.element("div").classes("card"):
                    section_title(
                        "One network. Three ways to think.", "Compare real algorithm outputs on the same sample graph"
                    )
                    with ui.element("div").classes("add-train-grid"):
                        origin = ui.select(self.web.station_options, label="Origin", value="BZA").props(
                            "outlined dense hide-bottom-space"
                        )
                        destination = ui.select(self.web.station_options, label="Destination", value="NDLS").props(
                            "outlined dense hide-bottom-space"
                        )
                        budget = (
                            ui.number("Branch & bound fare budget (INR)", value=3500, min=0, max=50000)
                            .props("outlined dense hide-bottom-space")
                            .style("grid-column:1/-1")
                        )
                    result_area = ui.element("div").classes("wide")

                    async def evaluate():
                        run_button.disable()
                        run_button.set_text("Running in a worker process…")
                        try:
                            results = await run.cpu_bound(
                                benchmark_lab, graph, origin.value, destination.value, int(budget.value or 0)
                            )
                            result_area.clear()
                            with result_area:
                                for result in results:
                                    with ui.element("div").classes("lab-result"):
                                        ui.label(result["algorithm"]).classes("lab-result-title")
                                        ui.label(
                                            " → ".join(result["path"]) if result["path"] else "No feasible path"
                                        ).classes("lab-path")
                                        metric = (
                                            (
                                                f"{result['cost']} minutes"
                                                if result["algorithm"].startswith("Branch")
                                                else money(result["cost"])
                                            )
                                            if result["cost"] is not None
                                            else "—"
                                        )
                                        with ui.element("div").classes("lab-meta"):
                                            ui.label(metric)
                                            ui.label(f"{result['visited']} states / relaxations")
                                            ui.label(f"{result['ms']:.4f} ms")
                                            ui.label(f"{result['pruned']} pruned")
                        except ValueError as e:
                            ui.notify(str(e), type="warning")
                        finally:
                            run_button.enable()
                            run_button.set_text("Run the algorithms")

                    run_button = (
                        button("Run the algorithms", evaluate, "primary", "code")
                        .classes("wide")
                        .style("margin-top:18px")
                        .mark("run-algorithms")
                    )
                    ui.label(
                        "Microtimings are measured locally on a small graph, not a production performance claim. DP allows ≤4 edges; branch & bound minimises minutes under your fare budget."
                    ).classes("booking-notice").style("margin-top:13px")
                with ui.element("div").classes("card"):
                    section_title("Keep the group together", "Backtracking with a deterministic fallback")
                    available = (
                        ui.input("Available seat numbers", value="1,2,3,5,6,8,9,10,11,12")
                        .props("outlined dense hide-bottom-space")
                        .classes("wide")
                    )
                    size = (
                        ui.number("Group size", value=3, min=1, max=6)
                        .props("outlined dense hide-bottom-space")
                        .classes("wide")
                        .style("margin-top:15px")
                    )
                    preference = (
                        ui.select(
                            {"together": "Together", "window": "Prefer window", "any": "Any available"},
                            value="together",
                            label="Preference",
                        )
                        .props("outlined dense hide-bottom-space")
                        .classes("wide")
                        .style("margin-top:15px")
                    )
                    seats_out = ui.element("div").classes("wide")

                    def allocate():
                        try:
                            seats = [int(v.strip()) for v in available.value.split(",") if v.strip()]
                            if not seats or any(s < 1 or s > 120 for s in seats):
                                raise ValueError("Use seat numbers between 1 and 120.")
                            chosen = allocate_seats(seats, int(size.value or 1), preference.value)
                            seats_out.clear()
                            with seats_out:
                                with ui.element("div").classes("lab-result"):
                                    ui.label("Allocation result").classes("lab-result-title")
                                    ui.label(
                                        ", ".join(seat_labels(chosen))
                                        if chosen
                                        else "Not enough seats — waitlist required"
                                    ).classes("lab-path")
                                    ui.label("No seats are reserved by this sandbox.").classes("tiny muted").style(
                                        "margin-top:8px"
                                    )
                        except (ValueError, TypeError) as e:
                            ui.notify(str(e), type="warning")

                    button("Try seat allocation", allocate, "secondary", "users").classes("wide").style(
                        "margin-top:18px"
                    )
                    ui.label(
                        "The search is bounded to six-seat coach rows. It tries a contiguous same-row group first; if that is impossible, it chooses the earliest free seats."
                    ).classes("booking-notice").style("margin-top:13px")
            patterns = [
                (
                    "Divide & conquer",
                    "Stable merge sort ranks train search results by fare, departure or duration. A higher-order key function makes one implementation reusable.",
                    "O(n log n) time · O(n) space",
                    "chart",
                ),
                (
                    "Dynamic programming",
                    "A bounded-edge shortest-path table reuses previous-layer answers. Useful when a maximum number of train legs is part of the problem.",
                    "O(H·E) relaxations + path copies",
                    "grid",
                ),
                (
                    "Greedy",
                    "Dijkstra settles the cheapest frontier using heapq. Correct for non-negative edge fares; not valid for arbitrary negative-cost graphs.",
                    "O((V+E) log V) textbook bound",
                    "map",
                ),
                (
                    "Backtracking",
                    "A constrained row search builds contiguous seat combinations, pruning impossible prefixes. It falls back rather than exploring the full coach combinatorially.",
                    "O(n log n) incl. sort · k ≤6",
                    "users",
                ),
                (
                    "Branch & bound",
                    "Finds the fastest simple path within a fare budget. An admissible remaining-time bound prunes branches; worst-case work is still exponential.",
                    "Exponential worst case · safety cap",
                    "code",
                ),
                (
                    "Data structures",
                    "Hash sets prevent seat overlap; a composite primary key enforces uniqueness. A deque models FIFO waitlists. Integer rupees keep fares exact.",
                    "Hash lookup expected O(1)",
                    "shield",
                ),
            ]
            with ui.element("div").classes("lab-pattern-grid"):
                for title, text, complexity, symbol in patterns:
                    with ui.element("div").classes("pattern-card"):
                        with ui.element("div").classes("stat-icon purple"):
                            icon(symbol)
                        ui.label(title).classes("pattern-title")
                        ui.label(text).classes("pattern-description")
                        ui.label(complexity).classes("complexity-pill")
            with ui.element("div").classes("lab-extra"):
                with ui.element("div").classes("card"):
                    section_title("Concurrency with a purpose", "Different workloads need different tools")
                    ui.markdown(
                        "### I/O-bound → threads\nDatabase and password operations run via `run.io_bound`. Independent reads are coordinated with `asyncio.gather`.\n\n### CPU-bound → processes\nThe benchmark above uses `run.cpu_bound`, a process pool, so it does not block the UI event loop.\n\n### Correctness → database transactions\nPostgreSQL row locks serialize conflicting reservations. Async code alone does **not** prevent double booking. The train → inventory → booking lock order avoids conflicting lock hierarchies."
                    ).classes("help-body")
                with ui.element("div").classes("card"):
                    section_title(
                        "Specification first. Validation always.", "The student can inspect and defend every decision"
                    )
                    ui.markdown(
                        "### Clear invariants\nSeat assignments must be unique; a request key is idempotent; canceled tickets release seats; only admins may change trains.\n\n### Systematic validation\nPytest unit/integration tests, Hypothesis properties, PostgreSQL race tests, browser end-to-end tests, coverage, Ruff and Mypy configuration are included.\n\n### Responsible AI assistance\nAI-generated code is a draft, not proof. The included review log records actual validation, limitations and prompting templates."
                    ).classes("help-body")

                    def download_guide():
                        path = ROOT / "docs" / "TECHNICAL_DEFENCE.md"
                        if path.exists():
                            ui.download(path, "Railora-Technical-Defence.md")
                        else:
                            ui.notify("The technical guide is in the project docs folder.", type="info")

                    button("Technical defence guide", download_guide, "text", "download").style("margin-top:10px")
            with ui.element("div").classes("project-badge"):
                icon("code")
                with ui.element("div"):
                    ui.label("The web interface is Python, too.").classes("project-badge-title")
                    ui.label(
                        "NiceGUI builds the frontend in Python. CSS handles styling; NiceGUI supplies the browser-side renderer. FastAPI and SQLAlchemy power the backend."
                    ).classes("project-badge-copy")


def register_lab_pages(web):
    lab = LabUI(web)

    @ui.page("/routes", title="Railora · Route explorer")
    async def routes():
        await lab.network()

    @ui.page("/lab", title="Railora · Algorithm lab")
    async def laboratory():
        await lab.laboratory()
