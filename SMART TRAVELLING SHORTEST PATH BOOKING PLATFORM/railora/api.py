"""REST API. The same Python services also power the NiceGUI frontend."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from railora.schemas import BookingInput, LoginInput, RegisterInput, TrainInput
from railora.services import AuthService, DomainError, RailService


def make_router(auth: AuthService, rail: RailService) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["Railora"])
    bearer = HTTPBearer(auto_error=False)

    def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict[str, Any]:
        return auth.current_user(credentials.credentials if credentials else None)

    UserDependency = Annotated[dict[str, Any], Depends(current_user)]

    @router.get("/health")
    def health():
        with rail.db.read() as session:
            from sqlalchemy import text

            session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": rail.db.engine.dialect.name,
            "payment": "simulated",
            "inventory": "academic demo",
        }

    @router.post("/login")
    def login(request: LoginInput):
        token, user = auth.login(request.email, request.password)
        return {"token": token, "user": user}

    @router.post("/register", status_code=201)
    def register(request: RegisterInput):
        token, user = auth.register(request)
        return {"token": token, "user": user}

    @router.get("/me")
    def me(user: UserDependency):
        return user

    @router.post("/logout")
    def logout(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], user: UserDependency):
        if credentials:
            auth.logout(credentials.credentials)
        return {"ok": True}

    @router.get("/stations")
    def stations():
        return rail.stations()

    @router.get("/trains")
    def trains(
        origin: str = "",
        destination: str = "",
        journey_date: date | None = None,
        travel_class: str = "CC",
        sort: str = "departure",
    ):
        return rail.search(origin, destination, journey_date, travel_class, sort)

    @router.get("/bookings")
    def bookings(user: UserDependency):
        return rail.bookings(user["id"])

    @router.post("/bookings", status_code=201)
    def book(request: BookingInput, user: UserDependency):
        return rail.create_booking(user["id"], request)

    @router.get("/bookings/{pnr}")
    def ticket(pnr: str, user: UserDependency):
        return rail.booking(user["id"], pnr)

    @router.post("/bookings/{pnr}/cancel")
    def cancel(pnr: str, user: UserDependency):
        return rail.cancel(user["id"], pnr)

    @router.post("/bookings/{pnr}/confirm")
    def confirm(pnr: str, user: UserDependency):
        return rail.confirm(user["id"], pnr)

    @router.get("/events")
    def events(user: UserDependency):
        return rail.events(user["id"])

    @router.get("/admin/stats")
    def stats(user: UserDependency):
        return rail.admin_stats(user["id"])

    @router.get("/admin/events")
    def admin_events(user: UserDependency):
        return rail.events(user["id"], admin=True)

    @router.get("/admin/trains")
    def all_trains(user: UserDependency):
        return rail.all_trains(user["id"])

    @router.post("/admin/trains", status_code=201)
    def add_train(request: TrainInput, user: UserDependency):
        return rail.add_train(user["id"], request)

    @router.post("/admin/trains/{train_id}/toggle")
    def toggle(train_id: int, user: UserDependency):
        return {"active": rail.toggle_train(user["id"], train_id)}

    @router.get("/admin/export")
    def export(user: UserDependency):
        from fastapi.responses import Response

        return Response(
            rail.export_bookings_csv(user["id"]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="railora-bookings.csv"'},
        )

    return router


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
