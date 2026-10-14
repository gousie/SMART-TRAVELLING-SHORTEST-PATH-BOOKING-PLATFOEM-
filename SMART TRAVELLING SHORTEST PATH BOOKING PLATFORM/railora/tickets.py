"""Generate a downloadable demo PDF ticket without external image dependencies."""

from io import BytesIO
from typing import Any

from reportlab.graphics.barcode import code128
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas


def ticket_pdf(booking: dict[str, Any]) -> bytes:
    stream = BytesIO()
    width, height = A5
    c = canvas.Canvas(stream, pagesize=A5)
    c.setTitle(f"Railora Demo Ticket {booking['pnr']}")
    c.setFillColor(HexColor("#6d4ce4"))
    c.rect(0, height - 90, width, 90, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 25)
    c.drawString(28, height - 42, "railora.")
    c.setFont("Helvetica", 10)
    c.drawString(28, height - 65, "DEMO E-TICKET - NOT VALID FOR TRAVEL")
    y = height - 125
    c.setFillColor(HexColor("#252333"))
    train = booking["train"]
    rows = [
        ("PNR", booking["pnr"]),
        ("Status", booking["status"].upper()),
        ("Train", f"{train['number']} - {train['name']}"),
        (
            "Route",
            f"{train['origin_city']} ({train['origin']}) to {train['destination_city']} ({train['destination']})",
        ),
        ("Date", booking["journey_date"]),
        ("Time", f"{train['departure']} - {train['arrival']}"),
        ("Class", booking["class_name"]),
        ("Seats", ", ".join(booking["seats"]) or "Not assigned"),
        ("Demo fare", f"INR {booking['fare']:,} (no real payment)"),
    ]
    for label, value in rows:
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#777384"))
        c.drawString(28, y, label)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(HexColor("#252333"))
        c.drawString(105, y, str(value)[:48])
        y -= 24
    c.setStrokeColor(HexColor("#dedbe8"))
    c.line(28, y + 5, width - 28, y + 5)
    y -= 24
    for i, p in enumerate(booking["passengers"], 1):
        c.setFont("Helvetica", 10)
        c.drawString(28, y, f"{i}. {p['name'][:35]}  |  {p['age']} years  |  {p['gender']}")
        y -= 19
    code128.Code128(booking["pnr"], barHeight=25, barWidth=0.9).drawOn(c, 28, 62)
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#777384"))
    c.drawString(28, 40, "Academic reservation simulation. Sample schedules and inventory only.")
    c.drawString(28, 28, "Not affiliated with Indian Railways or IRCTC. No real ticket is issued.")
    c.save()
    return stream.getvalue()
