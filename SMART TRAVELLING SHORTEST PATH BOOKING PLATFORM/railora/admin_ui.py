"""Live, role-protected operations workspace, authored entirely in Python."""

import asyncio
from typing import Any

from nicegui import run, ui
from pydantic import ValidationError

from railora.schemas import TrainInput
from railora.services import DomainError
from railora.web_components import (
    button,
    date_label,
    duration,
    icon,
    initials,
    money,
    page_heading,
    section_title,
    stat_card,
    status_badge,
)


class AdminUI:
    def __init__(self, web):
        self.web = web

    def chart_activity(self, stats: dict[str, Any]):
        options = {
            "backgroundColor": "transparent",
            "textStyle": {"fontFamily": "DM Sans"},
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "#fff",
                "borderColor": "#ece6f5",
                "textStyle": {"fontSize": 11, "color": "#8d759e"},
            },
            "grid": {"left": 33, "right": 15, "top": 25, "bottom": 25},
            "xAxis": {
                "type": "category",
                "data": stats["days"],
                "boundaryGap": False,
                "axisLine": {"show": False},
                "axisTick": {"show": False},
                "axisLabel": {"fontSize": 9, "color": "#b1a3c0", "margin": 14},
            },
            "yAxis": {
                "type": "value",
                "minInterval": 1,
                "axisLabel": {"fontSize": 9, "color": "#b1a3c0"},
                "splitLine": {"lineStyle": {"color": "#f1ecf6", "type": "dashed"}},
            },
            "series": [
                {
                    "name": "Bookings",
                    "type": "line",
                    "data": stats["daily_bookings"],
                    "smooth": 0.4,
                    "symbol": "circle",
                    "symbolSize": 5,
                    "showSymbol": False,
                    "lineStyle": {"color": "#8b65de", "width": 2.5},
                    "itemStyle": {"color": "#8b65de"},
                    "areaStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0,
                            "y": 0,
                            "x2": 0,
                            "y2": 1,
                            "colorStops": [{"offset": 0, "color": "#c6b1ed80"}, {"offset": 1, "color": "#efe8fa00"}],
                        }
                    },
                }
            ],
        }
        ui.echart(options).classes("wide").style("height:223px")

    def chart_status(self, stats):
        names = {
            "confirmed": "Confirmed",
            "reserved": "Reserved",
            "waitlisted": "Waitlisted",
            "cancelled": "Cancelled",
            "expired": "Expired",
        }
        colors = {
            "confirmed": "#9571df",
            "reserved": "#eec795",
            "waitlisted": "#98adf1",
            "cancelled": "#e8c9dc",
            "expired": "#d4cddd",
        }
        data = [
            {"name": names[k], "value": v, "itemStyle": {"color": colors[k]}} for k, v in stats["status_counts"].items()
        ]
        options = {
            "textStyle": {"fontFamily": "DM Sans"},
            "tooltip": {"trigger": "item"},
            "graphic": [
                {
                    "type": "text",
                    "left": "center",
                    "top": "36%",
                    "style": {
                        "text": str(stats["total_bookings"]),
                        "fill": "#6a4f86",
                        "fontSize": 30,
                        "fontWeight": 600,
                        "fontFamily": "DM Sans",
                    },
                },
                {
                    "type": "text",
                    "left": "center",
                    "top": "53%",
                    "style": {"text": "total bookings", "fill": "#b5a4c5", "fontSize": 9, "fontFamily": "DM Sans"},
                },
            ],
            "legend": {
                "bottom": 3,
                "left": "center",
                "icon": "circle",
                "itemWidth": 6,
                "itemHeight": 6,
                "itemGap": 12,
                "textStyle": {"color": "#a893bb", "fontSize": 9},
            },
            "series": [
                {
                    "type": "pie",
                    "radius": ["58%", "75%"],
                    "center": ["50%", "43%"],
                    "label": {"show": False},
                    "emphasis": {"scale": True, "scaleSize": 4},
                    "itemStyle": {"borderColor": "white", "borderWidth": 3, "borderRadius": 5},
                    "data": data,
                }
            ],
        }
        ui.echart(options).classes("wide").style("height:223px")

    def booking_rows(self, bookings):
        with ui.element("div").classes("table-scroll"):
            with ui.element("div").classes("table-head"):
                for label in ["PNR number", "Traveler", "Train / route", "Journey date", "Status", "Amount", ""]:
                    ui.label(label)
            for b in bookings:
                with ui.element("div").classes("data-row"):
                    ui.label(b["pnr"]).classes("pnr-cell")
                    with ui.element("div").classes("passenger-cell"):
                        ui.label(initials(b["passenger_name"])).classes("avatar")
                        ui.label(b["passenger_name"]).classes("name-cell")
                    with ui.element("div"):
                        ui.label(f"{b['train']['origin']} → {b['train']['destination']}").classes("train-cell-name")
                        ui.label(f"#{b['train']['number']} · {b['class_name']}").classes("train-cell-number")
                    ui.label(date_label(b["journey_date"], True))
                    status_badge(b["status"])
                    ui.label(money(b["fare"])).classes("name-cell")
                    button("", lambda b=b: self.web.ticket_dialog(b), "icon", "chevron").tooltip("View booking")

    @staticmethod
    def activity_items(events, limit=5):
        for event in events[:limit]:
            with ui.element("div").classes("activity-item"):
                with ui.element("div").classes("activity-symbol"):
                    icon("train" if not event["pnr"] else "ticket")
                with ui.element("div"):
                    ui.label(event["message"]).classes("activity-message")
                    ui.label(event["created_at"].replace("T", " ")[:16] + " UTC").classes("activity-time")

    async def export(self):
        try:
            user = await self.web.action_user()
            csv = await run.io_bound(self.web.rail.export_bookings_csv, user["id"])
            ui.download(csv.encode("utf-8-sig"), "railora-reservations.csv", media_type="text/csv")
        except DomainError as e:
            self.web.show_error(e)

    async def dashboard(self):
        user = await self.web.profile(admin=True)
        if not user:
            return
        with self.web.shell(user, "/admin", "Operations overview"):
            page_heading(
                f"Welcome back, {user['name'].split()[0]}",
                "A clear view of every journey.",
                "Your railway network, reservations and people — all moving together.",
            )
            last = {"id": 0}

            @ui.refreshable
            async def dashboard_body():
                stats, events = await asyncio.gather(
                    run.io_bound(self.web.rail.admin_stats, user["id"]),
                    run.io_bound(self.web.rail.events, user["id"], True, 8),
                )
                last["id"] = events[0]["id"] if events else 0
                with ui.element("div").classes("stats-grid four"):
                    stat_card(
                        "Total reservations",
                        str(stats["total_bookings"]),
                        "All-time · includes synthetic seed data",
                        "ticket",
                        "purple",
                    )
                    stat_card(
                        "Confirmed revenue",
                        money(stats["revenue"]),
                        "Simulated payments · not real earnings",
                        "wallet",
                        "green",
                    )
                    stat_card(
                        "Active train services",
                        f"{stats['active_trains']:02d}",
                        "Available across the station network",
                        "train",
                        "orange",
                    )
                    stat_card(
                        "Registered travelers",
                        f"{stats['users']:02d}",
                        "Traveler accounts in this demo",
                        "users",
                        "blue",
                    )
                with ui.element("div").classes("admin-chart-grid"):
                    with ui.element("div").classes("card chart-card"):
                        section_title("Booking activity", "A pulse on the last seven days")
                        with ui.element("div").classes("chart-legend"):
                            with ui.element("div"):
                                ui.element("i").classes("legend-dot")
                                ui.label("Reservations created")
                        self.chart_activity(stats)
                    with ui.element("div").classes("card chart-card"):
                        section_title("Reservation overview", "A live breakdown by status")
                        self.chart_status(stats)
                with ui.element("div").classes("admin-bottom-grid"):
                    with ui.element("div").classes("table-card"):
                        with ui.element("div").classes("table-toolbar"):
                            ui.label("Latest reservations").classes("section-title")
                            button("View all", lambda: ui.navigate.to("/admin/bookings"), "text", "arrow")
                        self.booking_rows(stats["bookings"][:6])
                        with ui.element("div").classes("table-footer"):
                            ui.label(
                                f"Showing latest {min(6, len(stats['bookings']))} of {len(stats['bookings'])} reservations"
                            )
                            button("Export CSV", self.export, "text", "download")
                    with ui.element("div").classes("card activity-card"):
                        with ui.element("div").classes("section-heading"):
                            ui.label("Live activity").classes("section-title")
                            with ui.element("div").classes("live-pill"):
                                ui.element("span").classes("status-dot")
                                ui.label("LIVE")
                        self.activity_items(events, 5)
                        button("View activity feed", lambda: ui.navigate.to("/admin/activity"), "text", "arrow").style(
                            "margin-top:12px"
                        )
                with ui.element("div").classes("project-badge"):
                    icon("shield")
                    with ui.element("div"):
                        ui.label("Built for reliability, designed to learn.").classes("project-badge-title")
                        ui.label(
                            "Atomic seat allocation · FIFO waitlist · Role-based access · Live updates every 3 seconds"
                        ).classes("project-badge-copy")

            await dashboard_body()

            async def poll():
                try:
                    events = await run.io_bound(self.web.rail.events, user["id"], True, 1)
                    if events and events[0]["id"] != last["id"]:
                        dashboard_body.refresh()
                except DomainError:
                    pass

            ui.timer(3, poll)

    async def trains_page(self):
        user = await self.web.profile(admin=True)
        if not user:
            return
        with self.web.shell(user, "/admin/trains", "Train management"):
            page_heading(
                "Keep the network moving",
                "Every train. Every connection.",
                "Manage sample services, pause new bookings, and grow your station network.",
            )
            with ui.element("div").classes("admin-actions"):
                button("Add a train", lambda: self.add_train_dialog(table.refresh), "primary", "train")
            with ui.element("div").classes("table-card trains-table"):
                with ui.element("div").classes("table-toolbar"):
                    ui.label("Train directory").classes("section-title")
                    with ui.element("div").classes("table-controls"):
                        query = ui.input(placeholder="Name or number...", on_change=lambda: table.refresh()).props(
                            "outlined dense hide-bottom-space"
                        )
                        status = ui.select(
                            {"all": "All services", "active": "Active only", "paused": "Paused only"},
                            value="all",
                            on_change=lambda: table.refresh(),
                        ).props("outlined dense hide-bottom-space")

                @ui.refreshable
                async def table():
                    trains = await run.io_bound(self.web.rail.all_trains, user["id"])
                    value = query.value.strip().lower()
                    trains = [
                        t
                        for t in trains
                        if value
                        in (
                            t["name"] + " " + t["number"] + " " + t["origin_city"] + " " + t["destination_city"]
                        ).lower()
                    ]
                    if status.value != "all":
                        trains = [t for t in trains if t["active"] == (status.value == "active")]
                    buttons = {}
                    with ui.element("div").classes("table-scroll"):
                        with ui.element("div").classes("table-head"):
                            for label in [
                                "Train service",
                                "Origin",
                                "Destination",
                                "Schedule",
                                "Base fare",
                                "Status",
                                "Action",
                            ]:
                                ui.label(label)
                        for t in trains:
                            with ui.element("div").classes("data-row"):
                                with ui.element("div"):
                                    ui.label(t["name"]).classes("train-cell-name")
                                    ui.label("#" + t["number"]).classes("train-cell-number")
                                ui.label(t["origin_city"] + " · " + t["origin"])
                                ui.label(t["destination_city"] + " · " + t["destination"])
                                with ui.element("div"):
                                    ui.label(t["departure"] + " → " + t["arrival"])
                                    ui.label(duration(t["duration"])).classes("train-cell-number")
                                ui.label(money(t["base_fare"]))
                                with ui.element("span").classes(
                                    "status-badge " + ("status-confirmed" if t["active"] else "status-cancelled")
                                ):
                                    ui.label("Active" if t["active"] else "Paused")

                                async def toggle(train=t):
                                    buttons[train["id"]].disable()
                                    try:
                                        profile = await self.web.action_user()
                                        active = await run.io_bound(
                                            self.web.rail.toggle_train, profile["id"], train["id"]
                                        )
                                        ui.notify(
                                            "New bookings "
                                            + ("enabled." if active else "paused. Existing tickets are unchanged."),
                                            type="positive",
                                        )
                                        table.refresh()
                                    except DomainError as e:
                                        self.web.show_error(e)
                                    finally:
                                        if not buttons[train["id"]].is_deleted:
                                            buttons[train["id"]].enable()

                                buttons[t["id"]] = button("Pause" if t["active"] else "Resume", toggle, "secondary")
                    if not trains:
                        self.web.empty_state("No services match", "Try another train number or filter.")
                    with ui.element("div").classes("table-footer"):
                        ui.label(f"{len(trains)} services · Sample timetables · All classes are simulated")
                        ui.label("Changes appear immediately in traveler searches")

                await table()

    async def add_train_dialog(self, refresh):
        with ui.dialog() as dialog, ui.card().classes("modal-card").style("width:620px"):
            with ui.element("div").classes("modal-header"):
                ui.label("Make room for a new journey.").classes("modal-title")
                button("Close", dialog.close, "text")
            ui.label(
                "Add a sample direct train. Timetables and fares are not verified against real railway services."
            ).classes("modal-subtitle")
            with ui.element("div").classes("add-train-grid"):
                number = ui.input("Train number", placeholder="Five digits").props("outlined dense hide-bottom-space")
                name = ui.input("Train name", placeholder="New express service").props(
                    "outlined dense hide-bottom-space"
                )
                origin = ui.select(self.web.station_options, label="Origin", value="BZA").props(
                    "outlined dense hide-bottom-space"
                )
                destination = ui.select(self.web.station_options, label="Destination", value="SC").props(
                    "outlined dense hide-bottom-space"
                )
                departure = ui.input("Departure", value="08:00").props("outlined dense type=time hide-bottom-space")
                arrival = ui.input("Arrival", value="12:00").props("outlined dense type=time hide-bottom-space")
                minutes = ui.number("Duration (minutes)", value=240, min=10, max=4320).props(
                    "outlined dense hide-bottom-space"
                )
                fare = ui.number("Base fare (INR)", value=600, min=50, max=15000).props(
                    "outlined dense hide-bottom-space"
                )
                capacity = ui.number("Seats per class", value=36, min=6, max=120).props(
                    "outlined dense hide-bottom-space"
                )

            async def save():
                add_button.disable()
                try:
                    profile = await self.web.action_user()
                    request = TrainInput(
                        number=number.value,
                        name=name.value,
                        origin=origin.value,
                        destination=destination.value,
                        departure=departure.value,
                        arrival=arrival.value,
                        duration=minutes.value,
                        base_fare=fare.value,
                        capacity=capacity.value,
                    )
                    await run.io_bound(self.web.rail.add_train, profile["id"], request)
                    dialog.close()
                    ui.notify("Train added to the station network.", type="positive")
                    refresh()
                except (DomainError, ValidationError) as e:
                    self.web.show_error(e)
                finally:
                    add_button.enable()

            with ui.element("div").classes("modal-actions"):
                button("Cancel", dialog.close, "secondary")
                add_button = button("Add train", save, "primary", "train")
        dialog.open()

    async def bookings_page(self):
        user = await self.web.profile(admin=True)
        if not user:
            return
        with self.web.shell(user, "/admin/bookings", "Reservations"):
            page_heading(
                "Every traveler matters",
                "Reservations, without the guesswork.",
                "Search tickets, review live status, and export your reservation register.",
            )
            with ui.element("div").classes("admin-actions"):
                button("Export reservations", self.export, "secondary", "download")
            with ui.element("div").classes("table-card"):
                with ui.element("div").classes("table-toolbar"):
                    ui.label("Reservation register").classes("section-title")
                    with ui.element("div").classes("table-controls"):
                        query = ui.input(placeholder="PNR or traveler...", on_change=lambda: table.refresh()).props(
                            "outlined dense hide-bottom-space"
                        )
                        status = ui.select(
                            {
                                "all": "All statuses",
                                "confirmed": "Confirmed",
                                "reserved": "Reserved",
                                "waitlisted": "Waitlisted",
                                "cancelled": "Cancelled",
                                "expired": "Expired",
                            },
                            value="all",
                            on_change=lambda: table.refresh(),
                        ).props("outlined dense hide-bottom-space")
                page = {"value": 0}

                @ui.refreshable
                async def table():
                    bookings = await run.io_bound(self.web.rail.bookings, user["id"], True)
                    value = query.value.lower().strip()
                    bookings = [
                        b
                        for b in bookings
                        if value in (b["pnr"] + " " + b["passenger_name"] + " " + b["train"]["number"]).lower()
                    ]
                    if status.value != "all":
                        bookings = [b for b in bookings if b["status"] == status.value]
                    max_page = max(0, (len(bookings) - 1) // 12)
                    page["value"] = min(page["value"], max_page)
                    start = page["value"] * 12
                    self.booking_rows(bookings[start : start + 12])
                    if not bookings:
                        self.web.empty_state("No reservations match", "Try a different PNR, traveler or status.")

                    def change(delta):
                        page["value"] = max(0, min(max_page, page["value"] + delta))
                        table.refresh()

                    with ui.element("div").classes("table-footer"):
                        ui.label(
                            f"Showing {min(start + 1, len(bookings))}–{min(start + 12, len(bookings))} of {len(bookings)} reservations"
                        )
                        with ui.element("div").style("display:flex;gap:12px"):
                            button("Previous", lambda: change(-1), "text")
                            button("Next", lambda: change(1), "text")

                await table()
            last = {"id": 0}

            async def poll():
                events = await run.io_bound(self.web.rail.events, user["id"], True, 1)
                new = events[0]["id"] if events else 0
                if last["id"] and new != last["id"]:
                    table.refresh()
                last["id"] = new

            ui.timer(3, poll)

    async def activity_page(self):
        user = await self.web.profile(admin=True)
        if not user:
            return
        with self.web.shell(user, "/admin/activity", "Live activity"):
            page_heading(
                "A network in motion",
                "Every update, as it happens.",
                "Persistent audit events from bookings, cancellations, waitlists and service changes.",
            )
            with ui.element("div").classes("card").style("max-width:850px"):
                with ui.element("div").classes("section-heading"):
                    ui.label("Operations timeline").classes("section-title")
                    with ui.element("div").classes("live-pill"):
                        ui.element("span").classes("status-dot")
                        ui.label("REFRESHES EVERY 3s")
                last = {"id": 0}

                @ui.refreshable
                async def feed():
                    events = await run.io_bound(self.web.rail.events, user["id"], True, 40)
                    last["id"] = events[0]["id"] if events else 0
                    self.activity_items(events, 40)

                await feed()

                async def poll():
                    events = await run.io_bound(self.web.rail.events, user["id"], True, 1)
                    if events and events[0]["id"] != last["id"]:
                        feed.refresh()

                ui.timer(3, poll)


def register_admin_pages(web):
    admin = AdminUI(web)

    @ui.page("/admin", title="Railora · Operations workspace")
    async def overview():
        await admin.dashboard()

    @ui.page("/admin/trains", title="Railora · Train management")
    async def trains():
        await admin.trains_page()

    @ui.page("/admin/bookings", title="Railora · Reservation register")
    async def bookings():
        await admin.bookings_page()

    @ui.page("/admin/activity", title="Railora · Live activity")
    async def activity():
        await admin.activity_page()
