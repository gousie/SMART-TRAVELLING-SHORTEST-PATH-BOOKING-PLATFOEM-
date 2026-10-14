"""Small reusable Python UI components; no JavaScript app or frontend framework."""

from datetime import date
from html import escape
from typing import Any

from nicegui import ui

ICONS = {
    "train": '<rect x="4" y="3" width="16" height="16" rx="4"/><path d="M4 12h16M9 3v9M15 3v9M8 19l-2 3M16 19l2 3"/><path d="M8 16h.01M16 16h.01"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "ticket": '<path d="M3 8V5h18v3a3 3 0 0 0 0 6v5H3v-5a3 3 0 0 0 0-6Z"/><path d="M15 5v2m0 3v2m0 3v4"/>',
    "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    "map": '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6ZM9 3v15m6-12v15"/>',
    "code": '<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-11 12a2 2 0 0 0 4 0"/>',
    "chevron": '<path d="m9 5 7 7-7 7"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M16 3v4M8 3v4M3 11h18"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "user": '<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
    "shield": '<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Z"/><path d="m8 12 3 3 5-6"/>',
    "spark": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
    "logout": '<path d="M9 3H3v18h6m5-14 5 5-5 5M7 12h12"/>',
    "chart": '<path d="M3 3v18h18M7 15l4-5 4 3 6-8"/>',
    "activity": '<path d="M2 12h4l3-9 6 18 3-9h4"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-1 1-2 1-2 3m0 3h.01"/>',
    "leaf": '<path d="M20 4c-2 0-2-1-5-1a9 9 0 0 0-9 9c0 5 4 7 8 6s6-6 6-14ZM4 21 15 10"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    "swap": '<path d="M3 7h17m-4-4 4 4-4 4M21 17H4m4-4-4 4 4 4"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "wallet": '<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 8h18m-5 4h5v5h-5v-5Zm1 2h.01M3 5l14-3v3"/>',
}


def icon(name: str, cls: str = ""):
    markup = f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, ICONS["train"])}</svg>'
    return ui.html(markup).classes(f"line-icon {cls}")


def button(text: str = "", action=None, kind: str = "primary", icon_name: str | None = None):
    b = ui.button(text, on_click=action).props("no-caps unelevated").classes(f"app-button {kind}-button")
    if icon_name:
        with b:
            icon(icon_name)
    return b


def money(amount: int) -> str:
    return f"₹{amount:,}"


def duration(minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"


def date_label(value: str | date, short: bool = False) -> str:
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return d.strftime("%d %b" if short else "%a, %d %b %Y")


def initials(name: str) -> str:
    return "".join(p[0] for p in name.split()[:2]).upper()


def page_heading(eyebrow: str, title: str, subtitle: str):
    with ui.element("div").classes("page-heading"):
        with ui.element("div"):
            ui.label(eyebrow.upper()).classes("eyebrow")
            ui.label(title).classes("page-title")
            ui.label(subtitle).classes("page-subtitle")
        with ui.element("div").classes("date-pill"):
            icon("calendar")
            from railora.config import today

            ui.label(today().strftime("%A, %d %b"))


def section_title(title: str, subtitle: str = "", action: str = "", on_click=None):
    with ui.element("div").classes("section-heading"):
        with ui.element("div"):
            ui.label(title).classes("section-title")
            if subtitle:
                ui.label(subtitle).classes("muted small")
        if action:
            button(action, on_click, "text", "arrow")


def stat_card(title: str, value: str, context: str, icon_name: str, tone: str = "purple"):
    with ui.element("div").classes("stat-card"):
        with ui.element("div").classes("stat-card-top"):
            ui.label(title).classes("stat-label")
            with ui.element("div").classes(f"stat-icon {tone}"):
                icon(icon_name)
        ui.label(value).classes("stat-value")
        ui.label(context).classes("stat-context")


def status_badge(status: str):
    with ui.element("span").classes(f"status-badge status-{status}"):
        ui.element("span").classes("status-dot")
        ui.label(status.capitalize())


def route_line(train: dict[str, Any], compact: bool = False):
    with ui.element("div").classes("route-line" + (" compact" if compact else "")):
        with ui.element("div").classes("route-end"):
            ui.label(train["departure"]).classes("route-time")
            ui.label(train["origin"]).classes("route-code")
            ui.label(train["origin_city"]).classes("route-city")
        with ui.element("div").classes("route-middle"):
            ui.label(duration(train["duration"])).classes("route-duration")
            ui.html('<div class="track"><i></i><span></span><b></b></div>')
            ui.label("Direct journey").classes("route-direct")
        with ui.element("div").classes("route-end right"):
            ui.label(train["arrival"]).classes("route-time")
            ui.label(train["destination"]).classes("route-code")
            ui.label(train["destination_city"]).classes("route-city")
            if train["duration"] >= 1440 or train["arrival"] < train["departure"]:
                ui.label(
                    f"+{max(1, (int(train['departure'][:2]) * 60 + int(train['departure'][3:]) + train['duration']) // 1440)} day"
                ).classes("tiny muted")


def network_svg(
    stations: list[dict[str, Any]], trains: list[dict[str, Any]], highlighted: list[str] | None = None
) -> str:
    highlight = highlighted or []
    points = {s["code"]: (100 + (s["lon"] - 72) * 36, 50 + (30 - s["lat"]) * 17) for s in stations}
    edges = set()
    lines = []
    for t in trains:
        pair = (t["origin"], t["destination"])
        if pair in edges:
            continue
        edges.add(pair)
        x1, y1 = points[pair[0]]
        x2, y2 = points[pair[1]]
        active = any(pair == tuple(highlight[i : i + 2]) for i in range(max(0, len(highlight) - 1)))
        bend = (x1 + x2) / 2 + 25
        lines.append(
            f'<path d="M{x1},{y1} Q{bend},{(y1 + y2) / 2} {x2},{y2}" fill="none" stroke="{"#7253e8" if active else "#c8c4da"}" stroke-width="{3 if active else 1.3}" opacity="{1 if active else 0.6}"/>'
        )
    markers = []
    for s in stations:
        x, y = points[s["code"]]
        markers.append(
            f'<circle cx="{x}" cy="{y}" r="9" fill="#f0ebff"/><circle cx="{x}" cy="{y}" r="4" fill="#7654dc" stroke="white" stroke-width="1.5"/><text x="{x + 13}" y="{y + 4}" font-size="11" fill="#625b78" font-family="DM Sans,sans-serif">{escape(s["city"])}</text>'
        )
    silhouette = '<path d="M290 40 310 50 355 48 390 75 375 110 410 145 375 172 353 210 337 267 315 319 285 377 263 355 246 296 211 240 193 198 147 160 134 125 169 107 174 77 231 69 259 42Z" fill="#f4f2fa" stroke="#e9e5f2" stroke-width="1.3"/>'
    dots = "".join(
        f'<circle cx="{x}" cy="{y}" r="1" fill="#ece8f4"/>' for x in range(25, 620, 20) for y in range(15, 420, 20)
    )
    return f'<svg viewBox="0 0 640 430" role="img" aria-label="Illustrative Indian railway station network">{dots}{silhouette}{"".join(lines)}{"".join(markers)}</svg>'
