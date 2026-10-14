"""End-to-end HTTP API integration through shared services and a real test DB."""

from railora.tickets import ticket_pdf


def test_api_health_stations_and_search(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/stations").json()) == 4
    trains = client.get("/api/trains", params={"origin": "NDLS", "destination": "AGC", "sort": "fare"}).json()
    assert len(trains) == 1
    assert trains[0]["available"] == 6
    assert client.get("/api/trains", params={"travel_class": "BAD"}).status_code == 400


def test_auth_api_rejects_unauthorised_and_invalid_login(client, user_header):
    assert client.get("/api/bookings").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.post("/api/login", json={"email": "user@example.com", "password": "wrong"}).status_code == 401
    assert client.get("/api/admin/stats", headers=user_header).status_code == 403
    assert client.get("/api/admin/events", headers=user_header).status_code == 403
    assert client.get("/api/admin/trains", headers=user_header).status_code == 403
    assert client.get("/api/me", headers=user_header).json()["role"] == "user"
    assert client.post("/api/logout", headers=user_header).status_code == 200
    assert client.get("/api/me", headers=user_header).status_code == 401


def test_registration_does_not_allow_role_escalation(client):
    body = {"name": "Registered Traveler", "email": "new@example.com", "password": "NewPass123", "role": "admin"}
    res = client.post("/api/register", json=body)
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "user"
    assert client.post("/api/register", json=body).status_code == 409
    body["email"] = "not-an-email"
    assert client.post("/api/register", json=body).status_code == 422


def test_booking_reservation_confirmation_cancel_and_admin_visibility(
    client, user_header, admin_header, request_factory
):
    request = request_factory(mode="reserve").model_dump(mode="json")
    res = client.post("/api/bookings", headers=user_header, json=request)
    assert res.status_code == 201
    b = res.json()
    assert b["status"] == "reserved"
    assert client.get("/api/bookings", headers=user_header).json()[0]["pnr"] == b["pnr"]
    assert client.get("/api/bookings/" + b["pnr"], headers=user_header).status_code == 200
    assert ticket_pdf(b).startswith(b"%PDF-")
    assert client.get("/api/admin/stats", headers=admin_header).json()["total_bookings"] == 1
    assert client.get("/api/admin/events", headers=admin_header).json()[0]["pnr"] == b["pnr"]
    assert client.post("/api/bookings/" + b["pnr"] + "/confirm", headers=user_header).json()["status"] == "confirmed"
    assert client.post("/api/bookings/" + b["pnr"] + "/cancel", headers=user_header).json()["status"] == "cancelled"
    assert client.get("/api/trains", params={"origin": "NDLS", "destination": "AGC"}).json()[0]["available"] == 6
    assert client.get("/api/events", headers=user_header).json()[0]["kind"] == "cancelled"
    assert client.get("/api/admin/export", headers=admin_header).headers["content-type"].startswith("text/csv")


def test_api_passenger_and_class_validation(client, user_header, request_factory):
    body = request_factory().model_dump(mode="json")
    body["passengers"][0]["age"] = 0
    assert client.post("/api/bookings", headers=user_header, json=body).status_code == 422
    body = request_factory().model_dump(mode="json")
    body["travel_class"] = "INVALID"
    assert client.post("/api/bookings", headers=user_header, json=body).status_code == 422
    body = request_factory().model_dump(mode="json")
    body["passengers"] = body["passengers"] * 7
    assert client.post("/api/bookings", headers=user_header, json=body).status_code == 422


def test_admin_can_add_toggle_train_and_user_cannot(client, admin_header, user_header):
    body = {
        "number": "22444",
        "name": "API Test Express",
        "origin": "NDLS",
        "destination": "JP",
        "departure": "08:00",
        "arrival": "10:00",
        "duration": 120,
        "base_fare": 600,
        "capacity": 12,
    }
    assert client.post("/api/admin/trains", headers=user_header, json=body).status_code == 403
    added = client.post("/api/admin/trains", headers=admin_header, json=body)
    assert added.status_code == 201
    train_id = added.json()["id"]
    assert client.post(f"/api/admin/trains/{train_id}/toggle", headers=admin_header).json()["active"] is False
    assert len(client.get("/api/admin/trains", headers=admin_header).json()) == 3
