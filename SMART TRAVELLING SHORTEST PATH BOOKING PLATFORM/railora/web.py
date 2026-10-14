"""Python-authored responsive frontend powered by NiceGUI.

The browser renderer is NiceGUI/Quasar; page composition, state and event handlers
are Python. Styling is local CSS and real locally cached web photography.
"""

from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from nicegui import app, run, ui
from pydantic import ValidationError

from railora.config import settings, today
from railora.schemas import BookingInput, PassengerInput, RegisterInput
from railora.services import CLASSES, AuthService, DomainError, RailService
from railora.tickets import ticket_pdf
from railora.web_components import (
    button,
    date_label,
    icon,
    initials,
    money,
    page_heading,
    route_line,
    section_title,
    stat_card,
    status_badge,
)


class RailUI:
    def __init__(self, auth: AuthService, rail: RailService) -> None:
        self.auth, self.rail = auth, rail
        self.stations = rail.stations()
        self.station_options = {
            s["code"]: f"{s['city']} ({s['code']})"
            for s in self.stations
        }

    @staticmethod
    def head() -> None:
        ui.add_head_html("""
        <link rel="stylesheet" href="/static/styles.css">
        <meta name="theme-color" content="#7250df">

        <style>
        body, body * {
        transition:
        background-color 0.2s ease,
        color 0.2s ease,
        border-color 0.2s ease;
        }

        /* DARK MODE */
        html[data-railora-theme="dark"] body {
        background: #10151c !important;
        color: #e6edf5 !important;
        }

        html[data-railora-theme="dark"] .workspace,
        html[data-railora-theme="dark"] .main-content {
        background: #10151c !important;
        color: #e6edf5 !important;
        }

        html[data-railora-theme="dark"] .sidebar,
        html[data-railora-theme="dark"] .topbar {
        background: #171f29 !important;
        color: #e6edf5 !important;
        border-color: #2b3543 !important;
        }

        html[data-railora-theme="dark"] .card,
        html[data-railora-theme="dark"] .stat-card,
        html[data-railora-theme="dark"] .train-card,
        html[data-railora-theme="dark"] .booking-card,
        html[data-railora-theme="dark"] .upcoming-card,
        html[data-railora-theme="dark"] .search-card,
        html[data-railora-theme="dark"] .filter-panel,
        html[data-railora-theme="dark"] .support-card,
        html[data-railora-theme="dark"] .travel-tip,
        html[data-railora-theme="dark"] .quick-route-card,
        html[data-railora-theme="dark"] .fare-card,
        html[data-railora-theme="dark"] .modal-card {
        background: #1a2430 !important;
        color: #e6edf5 !important;
        border-color: #303d4c !important;
        }

        html[data-railora-theme="dark"] .hero {
        background-color: #202839 !important;
        }

        html[data-railora-theme="dark"] .nav-link,
        html[data-railora-theme="dark"] .section-title,
        html[data-railora-theme="dark"] .train-name,
        html[data-railora-theme="dark"] .detail-value,
        html[data-railora-theme="dark"] .profile-name,
        html[data-railora-theme="dark"] .brand-name,
        html[data-railora-theme="dark"] .current,
        html[data-railora-theme="dark"] .auth-title,
        html[data-railora-theme="dark"] .modal-title {
        color: #e6edf5 !important;
        }

        html[data-railora-theme="dark"] .muted,
        html[data-railora-theme="dark"] .small,
        html[data-railora-theme="dark"] .train-number,
        html[data-railora-theme="dark"] .footer {
        color: #a7b4c5 !important;
        }

        html[data-railora-theme="dark"] input,
        html[data-railora-theme="dark"] textarea,
        html[data-railora-theme="dark"] .q-field__control,
        html[data-railora-theme="dark"] .q-field__native {
        background-color: #202c39 !important;
        color: #e6edf5 !important;
        border-color: #435164 !important;
        }

        html[data-railora-theme="dark"] .nav-link:hover,
        html[data-railora-theme="dark"] .nav-link.active {
        background: #293546 !important;
        }

        /* GREEN MODE */
        html[data-railora-theme="green"] body {
        background: #edf5ef !important;
        color: #183b2b !important;
        }

        html[data-railora-theme="green"] .workspace,
        html[data-railora-theme="green"] .main-content {
        background: #edf5ef !important;
        color: #183b2b !important;
        }

        html[data-railora-theme="green"] .sidebar,
        html[data-railora-theme="green"] .topbar {
        background: #dcebe0 !important;
        color: #183b2b !important;
        border-color: #c5ddcc !important;
        }

        html[data-railora-theme="green"] .card,
        html[data-railora-theme="green"] .stat-card,
        html[data-railora-theme="green"] .train-card,
        html[data-railora-theme="green"] .booking-card,
        html[data-railora-theme="green"] .upcoming-card,
        html[data-railora-theme="green"] .search-card,
        html[data-railora-theme="green"] .filter-panel,
        html[data-railora-theme="green"] .support-card,
        html[data-railora-theme="green"] .travel-tip,
        html[data-railora-theme="green"] .quick-route-card,
        html[data-railora-theme="green"] .fare-card,
        html[data-railora-theme="green"] .modal-card {
        background: #ffffff !important;
        color: #183b2b !important;
        border-color: #cce0d1 !important;
        }

        html[data-railora-theme="green"] .hero {
        background-color: #d7eadc !important;
        }

        html[data-railora-theme="green"] .nav-link,
        html[data-railora-theme="green"] .section-title,
        html[data-railora-theme="green"] .train-name,
        html[data-railora-theme="green"] .detail-value,
        html[data-railora-theme="green"] .profile-name,
        html[data-railora-theme="green"] .brand-name,
        html[data-railora-theme="green"] .current,
        html[data-railora-theme="green"] .auth-title,
        html[data-railora-theme="green"] .modal-title {
        color: #183b2b !important;
        }

        html[data-railora-theme="green"] .muted,
        html[data-railora-theme="green"] .small,
        html[data-railora-theme="green"] .train-number,
        html[data-railora-theme="green"] .footer {
        color: #527360 !important;
        }

        html[data-railora-theme="green"] input,
        html[data-railora-theme="green"] textarea,
        html[data-railora-theme="green"] .q-field__control,
        html[data-railora-theme="green"] .q-field__native {
        background-color: #f5faf6 !important;
        color: #183b2b !important;
        border-color: #b8d2bf !important;
        }

        html[data-railora-theme="green"] .nav-link:hover,
        html[data-railora-theme="green"] .nav-link.active {
        background: #c8e1cf !important;
        }

        /* Theme selector */
        .theme-picker {
        min-width: 115px;
        max-width: 145px;
        }

        .theme-picker .q-field__control {
        border-radius: 10px;
        }

        .auth-theme-picker {
        position: fixed;
        top: 18px;
        right: 20px;
        z-index: 1000;
        }

        @media (max-width: 700px) {
        .theme-picker {
        min-width: 95px;
        max-width: 110px;
        }

        .demo-tag {
        display: none !important;
        }

        .auth-theme-picker {
        top: 12px;
        right: 12px;
        }
        }
        </style>

        <script>
        (() => {
        const allowed = ["light", "dark", "green"];
        const saved = localStorage.getItem("railora-theme") || "light";
        document.documentElement.dataset.railoraTheme =
        allowed.includes(saved) ? saved : "light";
        })();
        </script>
        """)

        ui.colors(
            primary="#7250df",
            secondary="#9582b2",
            positive="#68ad86",
            negative="#ca7791",
        )

    def theme_picker(self, auth_page: bool = False) -> None:
        """Display a theme selector and remember the user's choice."""

        current_theme = app.storage.user.get("theme", "light")

        def change_theme(event):
            theme = event.value

            if theme not in ("light", "dark", "green"):
                theme = "light"

            app.storage.user["theme"] = theme

            ui.run_javascript(
                f"""
                document.documentElement.dataset.railoraTheme = '{theme}';
                localStorage.setItem('railora-theme', '{theme}');
                """
            )

        with ui.element("div").classes(
            "auth-theme-picker" if auth_page else ""
        ):
            ui.select(
                {
                    "light": "☀️ Light",
                    "dark": "🌙 Dark",
                    "green": "🌿 Green",
                },
                value=current_theme,
                on_change=change_theme,
            ).props("dense outlined options-dense").classes("theme-picker")

    async def profile(
        self,
        admin: bool = False,
        auto: bool = False,
    ) -> dict[str, Any] | None:
        token = app.storage.user.get("token")

        if (
            not token
            and auto
            and settings.demo_autosignin
            and not app.storage.user.get("signed_out")
        ):
            token, _ = await run.io_bound(
                self.auth.login,
                "aditya@railora.demo",
                "Railora@123",
            )
            app.storage.user["token"] = token

        try:
            user = await run.io_bound(self.auth.current_user, token)

            if admin and user["role"] != "admin":
                ui.navigate.to("/login?role=admin")
                return None

            return user

        except DomainError:
            ui.navigate.to("/login")
            return None

    async def action_user(self) -> dict[str, Any]:
        return await run.io_bound(
            self.auth.current_user,
            app.storage.user.get("token"),
        )

    async def logout(self) -> None:
        token = app.storage.user.get("token")

        if token:
            await run.io_bound(self.auth.logout, token)

        app.storage.user["token"] = None
        app.storage.user["signed_out"] = True
        ui.navigate.to("/login")

    @contextmanager
    def shell(
        self,
        user: dict[str, Any],
        path: str,
        title: str = "Overview",
    ):
        self.head()
        is_admin = user["role"] == "admin"

        def global_key(event):
            if (
                event.action.keydown
                and event.key.name == "/"
                and not (event.modifiers.ctrl or event.modifiers.meta)
            ):
                self.quick_search()

        ui.keyboard(on_key=global_key, repeating=False)

        with ui.element("aside").classes("sidebar") as sidebar:
            with ui.element("div").classes("brand"):
                with ui.element("div").classes("brand-symbol"):
                    icon("train")

                ui.html(
                    '<div class="brand-name">railora'
                    '<span class="brand-dot">.</span></div>'
                )

            ui.label(
                "OPERATIONS" if is_admin else "YOUR WORKSPACE"
            ).classes("nav-label")

            links = (
                [
                    ("Overview", "grid", "/admin"),
                    ("Train management", "train", "/admin/trains"),
                    ("Reservations", "ticket", "/admin/bookings"),
                    ("Live activity", "activity", "/admin/activity"),
                ]
                if is_admin
                else [
                    ("Overview", "grid", "/dashboard"),
                    ("Find trains", "search", "/search"),
                    ("My bookings", "ticket", "/bookings"),
                    ("Saved routes", "heart", "/saved"),
                ]
            )

            with ui.element("div").classes("nav-group"):
                for label, symbol, href in links:
                    with (
                        ui.button(
                            on_click=lambda p=href: ui.navigate.to(p)
                        )
                        .props("flat no-caps")
                        .classes(
                            "nav-link"
                            + (" active" if path == href else "")
                        )
                    ):
                        icon(symbol)
                        ui.label(label)

                        if label == "My bookings":
                            ui.label("Trips").classes("nav-count")

            ui.label("DISCOVER & LEARN").classes("nav-label")

            with ui.element("div").classes("nav-group"):
                for label, symbol, href in [
                    ("Route explorer", "map", "/routes"),
                    ("Algorithm lab", "code", "/lab"),
                ]:
                    with (
                        ui.button(
                            on_click=lambda p=href: ui.navigate.to(p)
                        )
                        .props("flat no-caps")
                        .classes(
                            "nav-link"
                            + (" active" if path == href else "")
                        )
                    ):
                        icon(symbol)
                        ui.label(label)

            with ui.element("div").classes("sidebar-bottom"):
                with ui.element("div").classes("support-card"):
                    icon("help")
                    ui.label(
                        "A little help on the way?"
                    ).classes("support-title")
                    ui.label(
                        "We’re here for every step of your journey."
                    ).classes("support-copy")
                    button(
                        "Get help",
                        self.help_dialog,
                        "text",
                        "arrow",
                    )

                button(
                    "Traveler workspace"
                    if is_admin
                    else "Admin workspace",
                    lambda: ui.navigate.to(
                        "/login?role=user"
                        if is_admin
                        else "/login?role=admin"
                    ),
                    "text",
                    "shield",
                ).classes("switch-workspace")

                with ui.element("div").classes("sidebar-profile"):
                    ui.label(initials(user["name"])).classes("avatar")

                    with ui.element("div").classes("profile-text"):
                        ui.label(user["name"]).classes("profile-role")
                        ui.label(
                            "Administrator"
                            if is_admin
                            else "Rail explorer"
                        ).classes("profile-role")

                    button(
                        "",
                        self.logout,
                        "icon",
                        "logout",
                    ).tooltip("Sign out")

        with ui.element("div").classes("workspace"):
            with ui.element("header").classes("topbar"):
                button(
                    "",
                    lambda: sidebar.classes(toggle="mobile-open"),
                    "icon",
                    "grid",
                ).classes("mobile-menu").tooltip("Open navigation")

                with ui.element("div").classes("topbar-breadcrumb"):
                    ui.label("Operations" if is_admin else "Workspace")
                    icon("chevron")
                    ui.label(title).classes("current")

                with ui.element("div").classes("topbar-actions"):
                    with (
                        ui.element("div")
                        .classes("global-search")
                        .on("click", self.quick_search)
                    ):
                        icon("search")
                        ui.label("Search trains or a PNR...")
                        ui.label("/").classes("search-shortcut")

                    self.theme_picker()
                    ui.label("DEMO WORKSPACE").classes("demo-tag")

                    button(
                        "",
                        lambda: self.notifications(user, is_admin),
                        "icon",
                        "bell",
                    ).tooltip("Notifications")

                    ui.element("div").classes("topbar-divider")

                    with (
                        ui.element("div")
                        .classes("avatar")
                        .on("click", lambda: self.account_dialog(user))
                    ):
                        ui.label(initials(user["name"]))

            with ui.element("main").classes("main-content"):
                yield

            with ui.element("footer").classes("footer"):
                with ui.element("div").classes("footer-status"):
                    ui.element("span").classes("status-dot")
                    ui.label(
                        f"{self.rail.db.engine.dialect.name.title()} "
                        "connected · Python powered"
                    )

                ui.label(
                    "Academic demo · Sample schedules · "
                    "Not affiliated with IRCTC"
                )

    def search_state(self) -> dict[str, Any]:
        return dict(
            app.storage.user.get(
                "search",
                {
                    "origin": "NDLS",
                    "destination": "AGC",
                    "date": (
                        today() + timedelta(days=1)
                    ).isoformat(),
                    "class": "CC",
                },
            )
        )

    def choose_route(
        self,
        origin: str,
        destination: str,
    ) -> None:
        state = self.search_state()
        state.update(origin=origin, destination=destination)
        app.storage.user["search"] = state
        ui.navigate.to("/search")

    def search_form(self, standalone: bool = False) -> None:
        state = self.search_state()

        with ui.element("div").classes(
            "search-card" + (" standalone" if standalone else "")
        ):
            with ui.element("div").classes("search-field"):
                with ui.element("div").classes("field-caption"):
                    icon("pin")
                    ui.label("FROM")

                origin = (
                    ui.select(
                        self.station_options,
                        value=state["origin"],
                    )
                    .props(
                        "borderless dense options-dense "
                        "hide-bottom-space"
                    )
                    .classes("search-select")
                    .mark("origin")
                )

            def swap():
                before = origin.value
                origin.set_value(destination.value)
                destination.set_value(before)

            button(
                "",
                swap,
                "icon",
                "swap",
            ).classes("swap-button").tooltip(
                "Swap origin and destination"
            )

            with ui.element("div").classes("search-field"):
                with ui.element("div").classes("field-caption"):
                    icon("pin")
                    ui.label("TO")

                destination = (
                    ui.select(
                        self.station_options,
                        value=state["destination"],
                    )
                    .props(
                        "borderless dense options-dense "
                        "hide-bottom-space"
                    )
                    .classes("search-select")
                    .mark("destination")
                )

            with ui.element("div").classes("search-field"):
                with ui.element("div").classes("field-caption"):
                    icon("calendar")
                    ui.label("JOURNEY DATE")

                journey = (
                    ui.input(value=state["date"])
                    .props(
                        f"type=date borderless dense hide-bottom-space "
                        f"min={today().isoformat()} "
                        f"max={(today() + timedelta(days=60)).isoformat()}"
                    )
                    .classes("search-select")
                    .mark("journey-date")
                )

            with ui.element("div").classes(
                "search-field no-border"
            ):
                with ui.element("div").classes("field-caption"):
                    icon("users")
                    ui.label("TRAVEL CLASS")

                travel_class = (
                    ui.select(
                        {
                            "CC": "AC Chair Car",
                            "3A": "AC 3 Tier",
                            "SL": "Sleeper",
                        },
                        value=state["class"],
                    )
                    .props(
                        "borderless dense options-dense "
                        "hide-bottom-space"
                    )
                    .classes("search-select")
                )

            def find():
                try:
                    chosen = date.fromisoformat(journey.value)

                    if origin.value == destination.value:
                        raise ValueError(
                            "Choose two different stations."
                        )

                    if not (
                        today()
                        <= chosen
                        <= today() + timedelta(days=60)
                    ):
                        raise ValueError(
                            "Please choose a date within "
                            "the next 60 days."
                        )

                except (ValueError, TypeError) as e:
                    ui.notify(
                        str(e) or "Enter a valid journey date.",
                        type="warning",
                    )
                    return

                app.storage.user["search"] = {
                    "origin": origin.value,
                    "destination": destination.value,
                    "date": journey.value,
                    "class": travel_class.value,
                }

                ui.navigate.to("/search")

            button(
                "Find trains",
                find,
                "primary",
                "search",
            ).mark("find-trains")

    def train_card(
        self,
        train: dict[str, Any],
        state: dict[str, Any],
        user: dict[str, Any],
    ) -> None:
        with ui.element("div").classes("train-card"):
            with ui.element("div").classes("train-card-top"):
                with ui.element("div").classes("train-title-wrap"):
                    with ui.element("div").classes("train-symbol"):
                        icon("train")

                    with ui.element("div"):
                        ui.label(train["name"]).classes("train-name")
                        ui.label(
                            f"#{train['number']} · "
                            f"{CLASSES[state['class']]}"
                        ).classes("train-number")

                with ui.element("div").classes(
                    "availability"
                    + (" low" if train["available"] < 10 else "")
                ):
                    ui.element("span").classes("status-dot")
                    ui.label(
                        f"{train['available']} seats available"
                        if train["available"]
                        else "Waitlist available"
                    )

            with ui.element("div").classes("train-card-main"):
                route_line(train)

                with ui.element("div").classes("train-action"):
                    ui.label(money(train["fare"])).classes("train-fare")
                    ui.label(
                        "per person · before fees"
                    ).classes("fare-note")

                    button(
                        "Book ticket"
                        if train["available"]
                        else "Join waitlist",
                        lambda: self.booking_dialog(
                            train,
                            state,
                            user,
                        ),
                        "primary",
                    ).mark(f"book-{train['number']}")

            with ui.element("div").classes("train-card-foot"):
                with ui.element("div"):
                    icon("shield")
                    ui.label("Secure booking")

                with ui.element("div"):
                    icon("ticket")
                    ui.label("Instant demo e-ticket")

                button(
                    "Save route",
                    lambda: self.save_route(
                        train["origin"],
                        train["destination"],
                    ),
                    "text",
                    "heart",
                ).classes("save-button")

    def save_route(
        self,
        origin: str,
        destination: str,
    ) -> None:
        favorites = list(app.storage.user.get("favorites", []))
        pair = f"{origin}:{destination}"

        if pair not in favorites:
            favorites.append(pair)

        app.storage.user["favorites"] = favorites
        ui.notify(
            "Route saved. Find it in Saved routes.",
            type="positive",
        )

    def upcoming_card(self, booking: dict[str, Any]) -> None:
        with ui.element("div").classes("upcoming-card"):
            with ui.element("div").classes("upcoming-top"):
                with ui.element("div").classes("upcoming-label"):
                    ui.label("YOUR NEXT JOURNEY").classes("eyebrow")
                    status_badge(booking["status"])

                route_line(booking["train"], compact=True)

            with ui.element("div").classes("upcoming-body"):
                ui.label(
                    booking["train"]["name"]
                ).classes("upcoming-train-name")

                with ui.element("div").classes("upcoming-date"):
                    icon("calendar")
                    ui.label(date_label(booking["journey_date"]))

                ui.element("div").classes("ticket-separator")

                with ui.element("div").classes("ticket-details"):
                    for label, value in [
                        ("PNR NUMBER", booking["pnr"]),
                        ("CLASS", booking["class_name"]),
                        (
                            "SEAT",
                            ", ".join(booking["seats"]) or "Waiting",
                        ),
                        (
                            "PASSENGERS",
                            f"{len(booking['passengers'])} traveler(s)",
                        ),
                    ]:
                        with ui.element("div"):
                            ui.label(label).classes("detail-label")
                            ui.label(value).classes("detail-value")

                button(
                    "View e-ticket",
                    lambda: self.ticket_dialog(booking),
                    "secondary",
                    "ticket",
                ).classes("wide")

    async def dashboard(self) -> None:
        user = await self.profile(auto=True)

        if not user:
            return

        if user["role"] == "admin":
            ui.navigate.to("/admin")
            return

        state = self.search_state()

        import asyncio

        bookings, trains = await asyncio.gather(
            run.io_bound(self.rail.bookings, user["id"]),
            run.io_bound(
                self.rail.search,
                state["origin"],
                state["destination"],
                date.fromisoformat(state["date"]),
                state["class"],
            ),
        )

        upcoming = sorted(
            [
                b
                for b in bookings
                if b["journey_date"] >= today().isoformat()
                and b["status"] in ("confirmed", "reserved")
            ],
            key=lambda b: b["journey_date"],
        )

        completed = [
            b
            for b in bookings
            if b["journey_date"] < today().isoformat()
            and b["status"] == "confirmed"
        ]

        with self.shell(user, "/dashboard"):
            page_heading(
                f"Hello, {user['name'].split()[0]}",
                "Where will the rails take you?",
                "A new place. A familiar face. Your next journey starts here.",
            )

            with ui.element("section").classes("hero"):
                with ui.element("div").classes("hero-content"):
                    with ui.element("div").classes("hero-eyebrow"):
                        icon("spark")
                        ui.label("LESS PLANNING. MORE POSSIBILITY.")

                    ui.label(
                        "Great journeys.\nBeautiful beginnings."
                    ).classes("hero-title")

                    ui.label(
                        "Find your perfect train, settle into your seat, "
                        "and let the world come to you."
                    ).classes("hero-description")

                    with ui.element("div").classes("hero-tags"):
                        with ui.element("div"):
                            icon("shield")
                            ui.label("Easy reservations")

                        with ui.element("div"):
                            icon("ticket")
                            ui.label("Instant e-tickets")

                        with ui.element("div"):
                            icon("leaf")
                            ui.label("Travel thoughtfully")

                    ui.label(
                        "Scenic inspiration · Landwasser Viaduct, Switzerland"
                    ).classes("hero-caption")

                self.search_form()

            with ui.element("div").classes("stats-grid"):
                stat_card(
                    "Upcoming journeys",
                    f"{len(upcoming):02d}",
                    "Your next adventure is waiting",
                    "ticket",
                    "purple",
                )

                stat_card(
                    "Places explored",
                    f"{len({b['train']['destination'] for b in completed}):02d}",
                    "One journey, a thousand memories",
                    "map",
                    "green",
                )

                stat_card(
                    "Your travel spend",
                    money(
                        sum(
                            b["fare"]
                            for b in bookings
                            if b["status"] == "confirmed"
                        )
                    ),
                    "All-time · simulated payments only",
                    "wallet",
                    "orange",
                )

            with ui.element("div").classes("dashboard-grid"):
                with ui.element("div"):
                    section_title(
                        "Recommended for your journey",
                        f"{self.city(state['origin'])} → "
                        f"{self.city(state['destination'])} · "
                        f"{date_label(state['date'], True)}",
                        "View all trains",
                        lambda: ui.navigate.to("/search"),
                    )

                    with ui.element("div").classes("train-list"):
                        for train in trains[:2]:
                            self.train_card(train, state, user)

                        if not trains:
                            self.empty_state(
                                "No direct trains here yet",
                                "Try a popular route or explore the station network.",
                            )

                    with ui.element("div").classes("popular-section"):
                        section_title(
                            "A little inspiration for your next trip",
                            "",
                            "Explore routes",
                            lambda: ui.navigate.to("/routes"),
                        )

                        with ui.element("div").classes("destination-grid"):
                            destinations = [
                                (
                                    "Jaipur",
                                    "Pink palaces. Golden memories.",
                                    "jaipur",
                                    "CULTURE",
                                    "NDLS",
                                    "JP",
                                    650,
                                ),
                                (
                                    "Goa",
                                    "Slow days by the ocean.",
                                    "goa",
                                    "COASTAL",
                                    "CSMT",
                                    "MAO",
                                    590,
                                ),
                                (
                                    "Kochi",
                                    "A greener kind of getaway.",
                                    "kerala",
                                    "NATURE",
                                    "SBC",
                                    "ERS",
                                    480,
                                ),
                            ]

                            for (
                                city,
                                desc,
                                photo,
                                tag,
                                origin,
                                destination,
                                fare,
                            ) in destinations:
                                with (
                                    ui.element("div")
                                    .classes("destination-card")
                                    .on(
                                        "click",
                                        lambda o=origin, d=destination:
                                        self.choose_route(o, d),
                                    )
                                ):
                                    with (
                                        ui.element("div")
                                        .classes("destination-photo")
                                        .style(
                                            "background-image:"
                                            f"url(/static/images/{photo}.webp)"
                                        )
                                    ):
                                        ui.label(tag).classes(
                                            "destination-pill"
                                        )

                                    with ui.element("div").classes(
                                        "destination-body"
                                    ):
                                        ui.label(city).classes(
                                            "destination-title"
                                        )
                                        ui.label(desc).classes(
                                            "destination-desc"
                                        )

                                        with ui.element("div").classes(
                                            "destination-bottom"
                                        ):
                                            ui.html(
                                                f"<span>From "
                                                f"<strong>{money(fare)}</strong>"
                                                f"</span>"
                                            )
                                            icon("arrow")

                with ui.element("div").classes("dashboard-right"):
                    section_title("Your upcoming trip")

                    if upcoming:
                        self.upcoming_card(upcoming[0])
                    else:
                        with ui.element("div").classes("upcoming-card"):
                            self.empty_state(
                                "Your window seat awaits",
                                "Book your first demo journey.",
                            )

                    with ui.element("div").classes("travel-tip"):
                        with ui.element("div").classes("tip-eyebrow"):
                            icon("spark")
                            ui.label("A LITTLE TRAVEL WISDOM")

                        ui.label(
                            "Good things come to those who travel."
                        ).classes("tip-title")

                        ui.label(
                            "Arrive 30 minutes early, pack a little lighter, "
                            "and always keep your ticket handy."
                        ).classes("tip-copy")

                        button(
                            "More travel tips",
                            self.help_dialog,
                            "text",
                            "arrow",
                        )

                    with ui.element("div").classes("quick-route-card"):
                        ui.label(
                            "Popular connections"
                        ).classes("section-title")

                        for origin, destination in [
                            ("BZA", "SC"),
                            ("GNT", "SC"),
                            ("MAS", "SBC"),
                        ]:
                            with (
                                ui.element("div")
                                .classes("quick-route-link")
                                .on(
                                    "click",
                                    lambda o=origin, d=destination:
                                    self.choose_route(o, d),
                                )
                            ):
                                icon("train")
                                ui.label(
                                    f"{self.city(origin)} → "
                                    f"{self.city(destination)}"
                                )
                                icon("chevron", "link-arrow")

    def city(self, code: str) -> str:
        return next(
            (
                station["city"]
                for station in self.stations
                if station["code"] == code
            ),
            code,
        )

    @staticmethod
    def empty_state(title: str, message: str):
        with ui.element("div").classes("route-empty"):
            icon("train")
            ui.label(title).classes("route-empty-title")
            ui.label(message).classes("small muted")

    async def search_page(self) -> None:
        user = await self.profile()

        if not user:
            return

        state = self.search_state()

        with self.shell(user, "/search", "Find trains"):
            page_heading(
                "A window to somewhere new",
                "Find your perfect journey.",
                "Compare trains, choose your class, and travel your way.",
            )

            self.search_form(standalone=True)

            with ui.element("div").classes("results-layout"):
                with ui.element("div"):

                    @ui.refreshable
                    async def results():
                        trains = await run.io_bound(
                            self.rail.search,
                            state["origin"],
                            state["destination"],
                            date.fromisoformat(state["date"]),
                            state["class"],
                            sort.value,
                        )

                        if available_only.value:
                            trains = [
                                train
                                for train in trains
                                if train["available"] > 0
                            ]

                        section_title(
                            f"{len(trains)} trains for your journey",
                            f"{self.city(state['origin'])} → "
                            f"{self.city(state['destination'])} · "
                            f"{date_label(state['date'])}",
                        )

                        with ui.element("div").classes("train-list"):
                            for train in trains:
                                self.train_card(train, state, user)

                            if not trains:
                                self.empty_state(
                                    "No trains match this search",
                                    "Try a different route, date or availability filter.",
                                )

                    target = ui.element("div").classes("wide")

                with ui.element("aside").classes("filter-panel"):
                    ui.label(
                        "Make it your kind of trip"
                    ).classes("section-title")

                    with ui.element("div").classes("filter-item"):
                        ui.label("Sort trains by").classes("filter-label")

                        sort = ui.select(
                            {
                                "departure": "Departure time",
                                "fare": "Lowest fare",
                                "duration": "Fastest journey",
                            },
                            value="departure",
                            on_change=lambda: results.refresh(),
                        ).props(
                            "outlined dense options-dense hide-bottom-space"
                        )

                    with ui.element("div").classes("filter-item"):
                        ui.label("Availability").classes("filter-label")

                        available_only = ui.checkbox(
                            "Only trains with seats",
                            value=False,
                            on_change=lambda: results.refresh(),
                        )

                    with ui.element("div").classes("notice"):
                        ui.label(
                            "Seats update at booking time. Reserve for "
                            "15 minutes or confirm instantly with a simulated payment."
                        )

                    button(
                        "Explore station network",
                        lambda: ui.navigate.to("/routes"),
                        "text",
                        "map",
                    ).style("margin-top:17px")

                with target:
                    await results()

    async def login_page(
        self,
        role: str = "user",
        register: bool = False,
    ) -> None:

        self.head()
        admin = role == "admin" and not register

        with ui.element("div").classes("auth-page"):
            # Left-side visual panel
            with ui.element("div").classes("auth-visual"):
                with ui.element("div").classes("brand"):
                    with ui.element("div").classes("brand-symbol"):
                        icon("train")

                    ui.html(
                        '<div class="brand-name">railora'
                        '<span class="brand-dot">.</span></div>'
                    )

                ui.label(
                    "THE JOURNEY IS THE DESTINATION"
                ).classes("auth-visual-caption")

                with ui.element("div"):
                    ui.label(
                        "The best stories\nstart on a train."
                    ).classes("auth-headline")

                    ui.label(
                        "From the everyday commute to the once-in-a-lifetime "
                        "escape. A simpler way to move, a better way to explore."
                    ).classes("auth-copy")

                    with ui.element("div").classes("auth-benefits"):
                        with ui.element("div"):
                            icon("shield")
                            ui.label("Secure reservations")

                        with ui.element("div"):
                            icon("ticket")
                            ui.label("Seamless journeys")

                        with ui.element("div"):
                            icon("map")
                            ui.label("Endless possibilities")

                with ui.element("div").classes("auth-visual-footer"):
                    ui.label("LESS PLANNING. MORE POSSIBILITY.")
                    ui.label("SWISS ALPS · SCENIC INSPIRATION")

            # IMPORTANT: These are siblings of auth-visual.
            # They must not be nested inside the auth-visual block.
            with ui.element("div").classes("auth-form-side"):
                self.theme_picker(auth_page=True)

                button(
                    "Back to workspace",
                    lambda: ui.navigate.to("/"),
                    "text",
                    "arrow",
                ).classes("auth-back")

                with ui.element("div").classes("auth-form"):
                    ui.label(
                        "YOUR NEXT CHAPTER STARTS HERE"
                    ).classes("eyebrow")

                    ui.label(
                        "Join the journey."
                        if register
                        else (
                            "Hello, operator."
                            if admin
                            else "Welcome aboard."
                        )
                    ).classes("auth-title")

                    ui.label(
                        "Create your account and find your next adventure."
                        if register
                        else (
                            "Your network. Your people. One workspace."
                            if admin
                            else "Sign in. Settle in. Let’s get you somewhere good."
                        )
                    ).classes("auth-subtitle")

                    if not register:

                        def role_changed(event):
                            is_admin = event.value == "admin"

                            email.set_value(
                                "admin@railora.demo"
                                if is_admin
                                else "aditya@railora.demo"
                            )

                            password.set_value(
                                "Admin@123"
                                if is_admin
                                else "Railora@123"
                            )

                        ui.toggle(
                            {
                                "user": "Traveler",
                                "admin": "Administrator",
                            },
                            value="admin" if admin else "user",
                            on_change=role_changed,
                        ).props(
                            "no-caps unelevated"
                        ).classes("auth-role")

                    name = None

                    if register:
                        ui.label("Full name").classes("auth-field-label")

                        name = (
                            ui.input(placeholder="Your full name")
                            .props(
                                "outlined dense hide-bottom-space "
                                "autocomplete=name"
                            )
                            .classes("auth-input")
                        )

                    ui.label("Email address").classes("auth-field-label")

                    email = (
                        ui.input(
                            value=(
                                ""
                                if register
                                else (
                                    "admin@railora.demo"
                                    if admin
                                    else "aditya@railora.demo"
                                )
                            ),
                            placeholder="you@example.com",
                        )
                        .props(
                            "outlined dense hide-bottom-space "
                            "type=email autocomplete=email"
                        )
                        .classes("auth-input")
                        .mark("login-email")
                    )

                    with email.add_slot("prepend"):
                        icon("user")

                    ui.label("Password").classes("auth-field-label")

                    password = (
                        ui.input(
                            value=(
                                ""
                                if register
                                else (
                                    "Admin@123"
                                    if admin
                                    else "Railora@123"
                                )
                            ),
                            placeholder="At least 8 characters",
                            password=True,
                            password_toggle_button=True,
                        )
                        .props(
                            "outlined dense hide-bottom-space "
                            "autocomplete=current-password"
                        )
                        .classes("auth-input")
                        .mark("login-password")
                    )

                    if not register:
                        with ui.element("div").classes("auth-options"):
                            ui.label(
                                "Session lasts 12 hours"
                            ).classes("tiny muted")

                            button(
                                "Need help signing in?",
                                self.signin_help,
                                "text",
                            )
                    else:
                        ui.element("div").style("height:20px")

                    async def submit():
                        submit_button.disable()

                        try:
                            if register:
                                payload = RegisterInput(
                                    name=name.value if name else "",
                                    email=email.value,
                                    password=password.value,
                                )

                                token, profile = await run.io_bound(
                                    self.auth.register,
                                    payload,
                                )
                            else:
                                token, profile = await run.io_bound(
                                    self.auth.login,
                                    email.value,
                                    password.value,
                                )

                            app.storage.user["token"] = token
                            app.storage.user["signed_out"] = False

                            ui.navigate.to(
                                "/admin"
                                if profile["role"] == "admin"
                                else "/dashboard"
                            )

                        except (DomainError, ValidationError) as e:
                            self.show_error(e)

                        finally:
                            submit_button.enable()

                    submit_button = (
                        button(
                            "Create account"
                            if register
                            else "Sign in to your workspace",
                            submit,
                            "primary",
                            "arrow",
                        )
                        .classes("auth-submit")
                        .mark("sign-in")
                    )

                    password.on("keydown.enter", submit)

                    if not register:
                        ui.label(
                            "or take a look around"
                        ).classes("auth-divider")

                        async def demo(chosen: str):
                            token, profile = await run.io_bound(
                                self.auth.login,
                                (
                                    "admin@railora.demo"
                                    if chosen == "admin"
                                    else "aditya@railora.demo"
                                ),
                                (
                                    "Admin@123"
                                    if chosen == "admin"
                                    else "Railora@123"
                                ),
                            )

                            app.storage.user["token"] = token
                            app.storage.user["signed_out"] = False

                            ui.navigate.to(
                                "/admin"
                                if chosen == "admin"
                                else "/dashboard"
                            )

                        with ui.element("div").classes("demo-buttons"):
                            button(
                                "Traveler demo",
                                lambda: demo("user"),
                                "secondary",
                                "user",
                            )

                            button(
                                "Admin demo",
                                lambda: demo("admin"),
                                "secondary",
                                "shield",
                            ).mark("admin-demo")

                    with ui.element("div").classes("auth-signup"):
                        ui.label(
                            "Already a traveler?"
                            if register
                            else "New to Railora?"
                        )

                        button(
                            "Sign in"
                            if register
                            else "Create an account",
                            lambda: ui.navigate.to(
                                "/login" if register else "/register"
                            ),
                            "text",
                        )

                    ui.label(
                        "An academic railway reservation demo. Sample trains, "
                        "simulated payments, real possibilities to learn."
                    ).classes("auth-disclaimer")

    @staticmethod
    def show_error(error: Exception) -> None:
        message = (
            error.message
            if isinstance(error, DomainError)
            else (
                "Please check your details: "
                + error.errors()[0]["msg"]
                if isinstance(error, ValidationError)
                else "Something went wrong. Please retry."
            )
        )

        ui.notify(message, type="negative", timeout=6000)

    def signin_help(self):
        with ui.dialog() as dialog, ui.card().classes("modal-card"):
            ui.label(
                "A little help signing in"
            ).classes("modal-title")

            ui.markdown(
                "**Traveler:** `aditya@railora.demo` · `Railora@123`\n\n"
                "**Administrator:** `admin@railora.demo` · `Admin@123`\n\n"
                "These are public demo accounts. Password reset and email "
                "delivery are not integrated. For a new account, choose "
                "**Create an account**."
            ).classes("help-body")

            button("Got it", dialog.close, "primary")

            dialog.open()

    async def booking_dialog(
        self,
        train: dict[str, Any],
        state: dict[str, Any],
        user: dict[str, Any],
    ):
        passenger_data = [
            {
                "name": user["name"],
                "age": 28,
                "gender": "Other",
            }
        ]

        request_key = str(uuid4())

        with ui.dialog() as dialog, ui.card().classes(
            "modal-card booking-modal"
        ):
            with ui.element("div").classes("booking-modal-head"):
                with ui.element("div").classes(
                    "modal-header"
                ).style("margin-bottom:8px"):
                    with ui.element("div"):
                        ui.label(
                            "Your next journey is almost here."
                        ).classes("modal-title")

                        ui.label(
                            f"#{train['number']} {train['name']} · "
                            f"{date_label(state['date'])}"
                        ).classes("modal-subtitle")

                    button("Close", dialog.close, "text")

                ui.label(
                    f"{train['origin_city']} → "
                    f"{train['destination_city']} · "
                    f"{train['departure']}–{train['arrival']}"
                ).classes("small muted")

            with ui.element("div").classes("booking-modal-layout"):
                with ui.element("div").classes("booking-form"):
                    ui.label(
                        "Passenger details"
                    ).classes("section-title")

                    def count_changed(event):
                        number = max(
                            1,
                            min(6, int(event.value or 1)),
                        )

                        while len(passenger_data) < number:
                            passenger_data.append(
                                {
                                    "name": "",
                                    "age": 28,
                                    "gender": "Other",
                                }
                            )

                        del passenger_data[number:]

                        passengers.refresh()
                        summary.refresh()

                    ui.number(
                        "Number of travelers",
                        value=1,
                        min=1,
                        max=6,
                        step=1,
                        on_change=count_changed,
                    ).props(
                        "outlined dense hide-bottom-space"
                    ).mark("passenger-count")

                    @ui.refreshable
                    def passengers():
                        for i, data in enumerate(passenger_data):
                
                            with ui.element("div").classes(
                                "passenger-row"
                            ):
                                ui.input(
                                    f"Traveler {i + 1}",
                                    value=data["name"],
                                    on_change=lambda e, d=data:
                                    d.update(name=e.value),
                                ).props(
                                    "outlined dense hide-bottom-space"
                                ).mark(f"passenger-name-{i}")

                                ui.number(
                                    "Age",
                                    value=data["age"],
                                    min=1,
                                    max=120,
                                    on_change=lambda e, d=data:
                                    d.update(age=e.value),
                                ).props(
                                    "outlined dense hide-bottom-space"
                                )

                                ui.select(
                                    ["Male", "Female", "Other"],
                                    label="Gender",
                                    value=data["gender"],
                                    on_change=lambda e, d=data:
                                    d.update(gender=e.value),
                                ).props(
                                    "outlined dense hide-bottom-space"
                                )

                    passengers()

                    travel_class = ui.select(
                        CLASSES,
                        label="Travel class",
                        value=state["class"],
                        on_change=lambda: summary.refresh(),
                    ).props("outlined dense hide-bottom-space")

                    ui.label("Seat preference").classes("small muted")

                    preference = ui.radio(
                        {
                            "together": "Keep us together",
                            "window": "Prefer window",
                            "any": "Any available",
                        },
                        value="together",
                    ).props("inline")

                    mode = ui.toggle(
                        {
                            "book": "Book & confirm",
                            "reserve": "Reserve for 15 min",
                        },
                        value="book",
                    ).props("no-caps unelevated")

                    allow_waitlist = ui.checkbox(
                        "Join waitlist if seats fill up",
                        value=True,
                    )

                    ui.label(
                        "Seats are assigned at confirmation. Preferences "
                        "are honoured where possible, not guaranteed."
                    ).classes("booking-notice")

                with ui.element("div"):

                    @ui.refreshable
                    async def summary():
                        quote = self.rail.fares.quote(
                            train["base_fare"],
                            travel_class.value,
                            len(passenger_data),
                        )

                        with ui.element("div").classes("fare-card"):
                            ui.label(
                                "Your fare, clearly explained"
                            ).classes("fare-heading")

                            for label, value in [
                                (
                                    f"{len(passenger_data)} × "
                                    f"{money(quote['ticket'])}",
                                    quote["subtotal"],
                                ),
                                ("Service fee", quote["fee"]),
                            ]:
                                with ui.element("div").classes("fare-row"):
                                    ui.label(label)
                                    ui.label(money(value))

                            with ui.element("div").classes("fare-total"):
                                ui.label("Total")
                                ui.label(money(quote["total"]))

                            ui.label(
                                "Demo payment only. No real money is charged "
                                "and no card details are collected."
                            ).classes("fare-footnote")

                        ui.label(
                            "A look at your coach"
                        ).classes("seat-map-label")

                        seats = await run.io_bound(
                            self.rail.seat_map,
                            train["id"],
                            date.fromisoformat(state["date"]),
                            travel_class.value,
                        )

                        with ui.element("div").classes("seat-map"):
                            for seat in seats:
                                ui.label(
                                    str(seat["number"]).zfill(2)
                                ).classes(
                                    "seat-square"
                                    + (" taken" if seat["taken"] else "")
                                )

                        ui.html(
                            '<div class="seat-legend">'
                            '<div><i></i> Available</div>'
                            '<div><i class="taken"></i> Taken</div>'
                            "</div>"
                        )

                        ui.label(
                            "Availability preview · updated at booking"
                        ).classes("fare-footnote")

                    await summary()

            with ui.element("div").classes("booking-modal-footer"):
                with ui.element("div").classes("booking-notice"):
                    icon("shield")
                    ui.label(
                        "Transaction-safe · No real payments"
                    )

                with ui.element("div").classes(
                    "modal-actions"
                ).style("margin-top:0"):
                    button("Not now", dialog.close, "secondary")

                    async def confirm_booking():
                        submit.disable()

                        try:
                            profile = await self.action_user()

                            request = BookingInput(
                                train_id=train["id"],
                                journey_date=date.fromisoformat(
                                    state["date"]
                                ),
                                travel_class=travel_class.value,
                                passengers=[
                                    PassengerInput(**p)
                                    for p in passenger_data
                                ],
                                mode=mode.value,
                                allow_waitlist=allow_waitlist.value,
                                preference=preference.value,
                                idempotency_key=request_key,
                            )

                            booking = await run.io_bound(
                                self.rail.create_booking,
                                profile["id"],
                                request,
                            )

                            dialog.close()

                            # Create the result dialog outside the
                            # now-closed booking dialog.
                            with ui.context.client.content:
                                self.booking_success(booking)

                        except (DomainError, ValidationError) as e:
                            self.show_error(e)

                        finally:
                            submit.enable()

                    submit = button(
                        "Confirm journey",
                        confirm_booking,
                        "primary",
                        "arrow",
                    ).mark("confirm-journey")

            dialog.open()

    def booking_success(self, booking: dict[str, Any]):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card success-card"
        ):
            with ui.element("div").classes("success-icon"):
                icon("check")

            ui.label(
                {
                    "confirmed": "You’re all set. Happy travels!",
                    "reserved": "Your seats are on hold.",
                    "waitlisted": "You’re on the waitlist.",
                }.get(booking["status"], "Journey updated")
            ).classes("modal-title")

            ui.label(
                "Your reservation has been saved and the admin "
                "workspace updated."
            ).classes("modal-subtitle")

            ui.label(booking["pnr"]).classes(
                "success-pnr"
            ).mark("new-pnr")

            ui.label(
                f"{booking['train']['origin_city']} → "
                f"{booking['train']['destination_city']} · "
                f"{date_label(booking['journey_date'], True)}"
            ).classes("small muted")

            if booking["status"] == "reserved":
                ui.label(
                    "Confirm within 15 minutes in My bookings, or "
                    "the seats will be released."
                ).classes("booking-notice")

            if booking["status"] == "waitlisted":
                ui.label(
                    "When seats open, you’ll receive a 15-minute hold. "
                    "Check My bookings or notifications."
                ).classes("booking-notice")

            with ui.element("div").classes("modal-actions"):
                button(
                    "View my bookings",
                    lambda: ui.navigate.to("/bookings"),
                    "primary",
                    "ticket",
                )

                button(
                    "Keep exploring",
                    lambda: ui.navigate.to("/dashboard"),
                    "secondary",
                )

            dialog.open()

    def ticket_dialog(self, booking: dict[str, Any]):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:510px"):
            with ui.element("div").classes("modal-header"):
                ui.label(
                    "Your journey at a glance"
                ).classes("modal-title")

                button("Close", dialog.close, "text")

            status_badge(booking["status"])

            ui.label(
                f"{booking['train']['number']} · "
                f"{booking['train']['name']}"
            ).classes("train-name")

            ui.element("div").style("height:10px")

            route_line(booking["train"])

            ui.label(
                f"{date_label(booking['journey_date'])} · "
                f"{booking['class_name']}"
            ).classes("small muted").style("margin:15px 0")

            ui.label(booking["pnr"]).classes(
                "success-pnr wide"
            ).style("text-align:center")

            for i, passenger in enumerate(booking["passengers"]):
                seat = (
                    booking["seats"][i]
                    if i < len(booking["seats"])
                    else "Not assigned"
                )

                ui.label(
                    f"{passenger['name']} · "
                    f"{passenger['age']} years · {seat}"
                ).classes("small muted")

            ui.label(
                f"Total {money(booking['fare'])} · Simulated payment"
            ).classes("small").style("margin-top:12px")

            ui.label(
                "DEMO E-TICKET · NOT VALID FOR TRAVEL"
            ).classes("booking-notice").style("margin-top:16px")

            async def download():
                try:
                    profile = await self.action_user()

                    fresh = await run.io_bound(
                        self.rail.booking,
                        profile["id"],
                        booking["pnr"],
                    )

                    pdf = await run.io_bound(ticket_pdf, fresh)

                    ui.download(
                        pdf,
                        f"Railora-{booking['pnr']}.pdf",
                        media_type="application/pdf",
                    )

                except DomainError as e:
                    self.show_error(e)

            button(
                "Download PDF ticket",
                download,
                "primary",
                "download",
            ).classes("wide").style("margin-top:16px")

            dialog.open()

    async def cancel_dialog(self, booking: dict[str, Any], refresh):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:420px"):
            ui.label("A change of plans?").classes("modal-title")

            ui.label(
                f"Cancel {booking['pnr']}? Your seats will be released "
                "and the admin notified. Any refund is simulated."
            ).classes("help-body")

            async def cancel():
                cancel_button.disable()

                try:
                    profile = await self.action_user()

                    await run.io_bound(
                        self.rail.cancel,
                        profile["id"],
                        booking["pnr"],
                    )

                    dialog.close()

                    ui.notify(
                        "Booking cancelled. Seats released.",
                        type="positive",
                    )

                    refresh()

                except DomainError as e:
                    self.show_error(e)

                finally:
                    cancel_button.enable()

            with ui.element("div").classes("modal-actions"):
                button(
                    "Keep my journey",
                    dialog.close,
                    "secondary",
                )

                cancel_button = button(
                    "Cancel booking",
                    cancel,
                    "danger",
                )

            dialog.open()

    async def bookings_page(self):
        user = await self.profile()

        if not user:
            return

        with self.shell(user, "/bookings", "My bookings"):
            page_heading(
                "Your travel journal",
                "Every journey, in one place.",
                "Tickets, reservations and little moments to look forward to.",
            )

            filter_state = {"value": "All"}

            with ui.element("div").classes("booking-toolbar"):
                with ui.element("div").classes("filter-tabs"):
                    tabs = {}

                    def choose(value):
                        filter_state["value"] = value

                        for label, tab in tabs.items():
                            tab.classes(
                                add="active" if label == value else "",
                                remove=(
                                    "active"
                                    if label != value
                                    else ""
                                ),
                            )

                        booking_list.refresh()

                    for label in [
                        "All",
                        "Upcoming",
                        "Past",
                        "Waitlisted",
                        "Cancelled",
                    ]:
                        tabs[label] = button(
                            label,
                            lambda v=label: choose(v),
                            "text",
                        ).classes(
                            "filter-tab"
                            + (" active" if label == "All" else "")
                        )

                button(
                    "Find a new journey",
                    lambda: ui.navigate.to("/search"),
                    "primary",
                    "search",
                )

            @ui.refreshable
            async def booking_list():
                bookings = await run.io_bound(
                    self.rail.bookings,
                    user["id"],
                )

                selected = filter_state["value"]

                if selected == "Upcoming":
                    bookings = [
                        b
                        for b in bookings
                        if b["journey_date"] >= today().isoformat()
                        and b["status"] in ("confirmed", "reserved")
                    ]

                elif selected == "Past":
                    bookings = [
                        b
                        for b in bookings
                        if b["journey_date"] < today().isoformat()
                    ]

                elif selected == "Waitlisted":
                    bookings = [
                        b for b in bookings
                        if b["status"] == "waitlisted"
                    ]

                elif selected == "Cancelled":
                    bookings = [
                        b for b in bookings
                        if b["status"] in ("cancelled", "expired")
                    ]

                if not bookings:
                    self.empty_state(
                        "A new journey is waiting",
                        "No bookings in this view. Find a train to get started.",
                    )

                with ui.element("div").classes("booking-grid"):
                    for booking in bookings:
                        with ui.element("div").classes("booking-card"):
                            with ui.element("div").classes(
                                "booking-card-head"
                            ):
                                ui.label(
                                    booking["pnr"]
                                ).classes("small muted")

                                status_badge(booking["status"])

                            ui.label(
                                booking["train"]["name"]
                            ).classes("train-name")

                            ui.label(
                                f"#{booking['train']['number']} · "
                                f"{date_label(booking['journey_date'])}"
                            ).classes("train-number")

                            route_line(booking["train"])

                            with ui.element("div").classes(
                                "booking-card-info"
                            ):
                                ui.label(booking["class_name"])

                                ui.label(
                                    f"{len(booking['passengers'])} traveler(s)"
                                )

                                ui.label(money(booking["fare"]))

                            if booking["expires_at"]:
                                ui.label(
                                    "15-minute hold · Confirm before "
                                    + booking["expires_at"][11:16]
                                    + " UTC"
                                ).classes("booking-notice")

                            with ui.element("div").classes(
                                "booking-card-actions"
                            ):
                                if booking["status"] == "reserved":

                                    async def confirm(
                                        pnr=booking["pnr"],
                                    ):
                                        try:
                                            profile = await self.action_user()

                                            await run.io_bound(
                                                self.rail.confirm,
                                                profile["id"],
                                                pnr,
                                            )

                                            ui.notify(
                                                "Journey confirmed. "
                                                "Demo payment successful.",
                                                type="positive",
                                            )

                                            booking_list.refresh()

                                        except DomainError as e:
                                            self.show_error(e)

                                    button(
                                        "Confirm reservation",
                                        confirm,
                                        "primary",
                                    )

                                if (
                                    booking["status"]
                                    in (
                                        "confirmed",
                                        "reserved",
                                        "waitlisted",
                                    )
                                    and booking["journey_date"]
                                    >= today().isoformat()
                                ):
                                    button(
                                        "Cancel",
                                        lambda b=booking:
                                        self.cancel_dialog(
                                            b,
                                            booking_list.refresh,
                                        ),
                                        "text",
                                    )

                                button(
                                    "View ticket",
                                    lambda b=booking:
                                    self.ticket_dialog(b),
                                    "secondary",
                                    "ticket",
                                )

            await booking_list()

            last_event = {"id": 0}

            async def poll():
                events = await run.io_bound(
                    self.rail.events,
                    user["id"],
                    False,
                    1,
                )

                newest = events[0]["id"] if events else 0

                if last_event["id"] and newest != last_event["id"]:
                    booking_list.refresh()

                last_event["id"] = newest

            ui.timer(5, poll)

    async def saved_page(self):
        user = await self.profile()

        if not user:
            return

        with self.shell(user, "/saved", "Saved routes"):
            page_heading(
                "The places you keep coming back to",
                "Your favorite connections.",
                "Save a route once. Find your next train in a moment.",
            )

            @ui.refreshable
            def favorites():
                saved = list(
                    app.storage.user.get("favorites", [])
                )

                if not saved:
                    self.empty_state(
                        "Keep your favorite routes close",
                        "Choose “Save route” on any train card. "
                        "Saved routes are stored for this browser session.",
                    )

                with ui.element("div").classes("booking-grid"):
                    for pair in saved:
                        origin, destination = pair.split(":")

                        with ui.element("div").classes("card"):
                            with ui.element("div").classes(
                                "stat-icon purple"
                            ):
                                icon("heart")

                            ui.label(
                                f"{self.city(origin)} → "
                                f"{self.city(destination)}"
                            ).classes("section-title").style(
                                "margin:15px 0 5px"
                            )

                            ui.label(
                                f"{origin} → {destination}"
                            ).classes("small muted")

                            def remove(key=pair):
                                app.storage.user["favorites"] = [
                                    item
                                    for item in app.storage.user.get(
                                        "favorites", []
                                    )
                                    if item != key
                                ]

                                favorites.refresh()

                            with ui.element("div").classes("modal-actions"):
                                button(
                                    "Remove",
                                    remove,
                                    "text",
                                )

                                button(
                                    "Find trains",
                                    lambda o=origin, d=destination:
                                    self.choose_route(o, d),
                                    "primary",
                                    "search",
                                )

            favorites()

    def help_dialog(self):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:610px"):
            with ui.element("div").classes("modal-header"):
                ui.label(
                    "Here for your journey."
                ).classes("modal-title")

                button("Close", dialog.close, "text")

            ui.markdown(
                "### A smoother start\n"
                "Arrive around 30 minutes early, check your platform and "
                "carry your ticket and ID.\n\n"
                "### How this project works\n"
                "Search a direct route, choose a class, add up to six "
                "travelers, and book or reserve. Holds last **15 minutes**. "
                "Full trains have a **FIFO waitlist**. Cancellations release "
                "seats and can promote waiting travelers.\n\n"
                "### A responsible demo\n"
                "Train schedules, fares and passengers are **sample data**. "
                "All payments, tickets and refunds are simulated. There is "
                "no IRCTC or live railway integration. Real scenic web "
                "photographs are cached locally for fast loading.\n\n"
                "### Built to learn\n"
                "Python/NiceGUI frontend, FastAPI, PostgreSQL, OOP strategies, "
                "functional algorithms and concurrency. Open **Algorithm lab** "
                "for the technical demonstration."
            ).classes("help-body")

            button(
                "Explore the algorithm lab",
                lambda: ui.navigate.to("/lab"),
                "primary",
                "code",
            )

            dialog.open()

    def account_dialog(self, user):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:400px"):
            ui.label(
                "Your Railora account"
            ).classes("modal-title")

            ui.label(user["name"]).classes("section-title")
            ui.label(user["email"]).classes("small muted")

            ui.label(
                f"Role: {user['role']} · Secure 12-hour session"
            ).classes("small muted")

            with ui.element("div").classes("modal-actions"):
                button("Close", dialog.close, "secondary")

                button(
                    "Sign out",
                    self.logout,
                    "text",
                    "logout",
                )

            dialog.open()

    async def notifications(self, user, admin=False):
        events = await run.io_bound(
            self.rail.events,
            user["id"],
            admin,
        )

        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:520px;max-height:80vh;overflow:auto"):
            with ui.element("div").classes("modal-header"):
                ui.label(
                    "The latest on your journey"
                ).classes("modal-title")

                button("Close", dialog.close, "text")

            if not events:
                ui.label(
                    "All quiet for now. Your booking updates "
                    "will appear here."
                ).classes("small muted")

            for event in events[:12]:
                with ui.element("div").classes("notification-item"):
                    with ui.element("div").classes("stat-icon purple"):
                        icon(
                            "ticket" if event["pnr"] else "train"
                        )

                    with ui.element("div"):
                        ui.label(
                            event["message"]
                        ).classes("notification-copy")

                        ui.label(
                            event["created_at"].replace("T", " ")[:16]
                            + " UTC"
                        ).classes("notification-date")

            dialog.open()

    def quick_search(self):
        with ui.dialog() as dialog, ui.card().classes(
            "modal-card"
        ).style("width:480px"):
            ui.label(
                "Where can we take you?"
            ).classes("modal-title")

            query = (
                ui.input(
                    placeholder="Train number, station or PNR..."
                )
                .props("outlined dense autofocus")
                .classes("wide")
            )

            result_area = ui.element("div").classes("wide")

            async def search():
                with result_area:
                    result_area.clear()

                    user = await self.action_user()
                    value = query.value.strip().lower()

                    if not value:
                        ui.label(
                            "Enter a train number, station, or PNR."
                        ).classes("small muted")
                        return

                    if value.startswith("rr"):
                        try:
                            booking = await run.io_bound(
                                self.rail.booking,
                                user["id"],
                                value.upper(),
                            )

                            dialog.close()
                            self.ticket_dialog(booking)

                        except DomainError as e:
                            self.show_error(e)

                        return

                    trains = await run.io_bound(self.rail.search)

                    matches = [
                        train
                        for train in trains
                        if value
                        in " ".join(
                            [
                                train["number"],
                                train["name"],
                                train["origin_city"],
                                train["destination_city"],
                            ]
                        ).lower()
                    ]

                    for train in matches[:6]:
                        button(
                            f"#{train['number']} · "
                            f"{train['origin_city']} → "
                            f"{train['destination_city']}",
                            lambda t=train: self.choose_route(
                                t["origin"],
                                t["destination"],
                            ),
                            "text",
                        )

                    if not matches:
                        ui.label(
                            "No matching trains. Try a station such as Vijayawada."
                        ).classes("small muted")

            query.on("keydown.enter", search)

            button(
                "Search",
                search,
                "primary",
                "search",
            )

            dialog.open()


def register_pages(
    auth: AuthService,
    rail: RailService,
):
    web = RailUI(auth, rail)

    @ui.page("/", title="Traveller · Journeys made simple")
    async def index():
        await web.dashboard()

    @ui.page("/dashboard", title="Traveller · Your workspace")
    async def dashboard():
        await web.dashboard()

    @ui.page("/login", title="Traveller · Welcome aboard")
    async def login(role: str = "user"):
        await web.login_page(role)

    @ui.page("/register", title="Traveller· Join the journey")
    async def register():
        await web.login_page(register=True)

    @ui.page("/search", title="Traveller · Find trains")
    async def search():
        await web.search_page()

    @ui.page("/bookings", title="Traveller · My bookings")
    async def bookings():
        await web.bookings_page()

    @ui.page("/saved", title="Traveller · Saved routes")
    async def saved():
        await web.saved_page()

    from railora.admin_ui import register_admin_pages
    from railora.lab_ui import register_lab_pages

    register_admin_pages(web)
    register_lab_pages(web)

    return web