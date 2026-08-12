from datetime import date

from fastapi import APIRouter, Query, status

from app.api.deps import Actor, DbSession, OrganizationId
from app.core.logging import log_event
from app.models.enums import ReservationSource, ReservationStatus
from app.schemas.common import Message, Page
from app.schemas.reservation import (
    CalendarResponse,
    DailyReservations,
    ReservationCreate,
    ReservationDetail,
    ReservationUpdate,
)
from app.services import reservations as service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=Page[ReservationDetail])
def list_reservations(
    db: DbSession,
    organization_id: OrganizationId,
    property_id: int | None = None,
    unit_id: int | None = None,
    from_date: date | None = Query(default=None, description="Stay overlaps this date onward"),
    to_date: date | None = Query(default=None, description="Stay starts on or before this date"),
    reservation_status: ReservationStatus | None = Query(default=None, alias="status"),
    source: ReservationSource | None = None,
    search: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> Page[ReservationDetail]:
    rows, total = service.list_reservations(
        db,
        organization_id=organization_id,
        property_id=property_id,
        unit_id=unit_id,
        from_date=from_date,
        to_date=to_date,
        reservation_status=reservation_status,
        source=source,
        search=search,
        limit=limit,
        offset=offset,
    )
    return Page[ReservationDetail](
        items=[service.to_detail(r) for r in rows], total=total, limit=limit, offset=offset
    )


# NOTE: the two static paths below must stay above /{reservation_id}.


@router.get("/daily", response_model=DailyReservations)
def daily(
    db: DbSession,
    organization_id: OrganizationId,
    date_: date = Query(default_factory=date.today, alias="date"),
    property_id: int | None = None,
) -> DailyReservations:
    """Arrivals, departures and in-house stays for one day."""
    arrivals, departures, in_house = service.daily_reservations(
        db, target_date=date_, organization_id=organization_id, property_id=property_id
    )
    return DailyReservations(
        date=date_,
        property_id=property_id,
        arrivals=[service.to_detail(r) for r in arrivals],
        departures=[service.to_detail(r) for r in departures],
        in_house=[service.to_detail(r) for r in in_house],
    )


@router.get("/calendar", response_model=CalendarResponse)
def calendar(
    db: DbSession,
    organization_id: OrganizationId,
    property_id: int,
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
) -> CalendarResponse:
    """Condensed month grid: one row per unit, reservations as spanning blocks."""
    return service.build_calendar(
        db, property_id=property_id, year=year, month=month, organization_id=organization_id
    )


@router.post("", response_model=ReservationDetail, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
) -> ReservationDetail:
    reservation = service.create_reservation(
        db, payload, organization_id=organization_id, actor=actor
    )
    return service.to_detail(reservation)


@router.get("/{reservation_id}", response_model=ReservationDetail)
def get_reservation(
    reservation_id: int, db: DbSession, organization_id: OrganizationId
) -> ReservationDetail:
    return service.to_detail(service.get_or_404(db, reservation_id, organization_id))


@router.patch("/{reservation_id}", response_model=ReservationDetail)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
) -> ReservationDetail:
    reservation = service.get_or_404(db, reservation_id, organization_id)
    updated = service.update_reservation(
        db, reservation, payload, organization_id=organization_id, actor=actor
    )
    return service.to_detail(updated)


@router.delete("/{reservation_id}", response_model=Message)
def delete_reservation(
    reservation_id: int, db: DbSession, organization_id: OrganizationId, actor: Actor
) -> Message:
    """Hard delete. Prefer PATCH to status=canceled/no_show to keep history."""
    reservation = service.get_or_404(db, reservation_id, organization_id)
    log_event(
        db,
        entity_type="reservation",
        entity_id=reservation.id,
        action="deleted",
        actor=actor,
        organization_id=organization_id,
        changes={"status": reservation.status, "source": reservation.source},
    )
    db.delete(reservation)
    return Message(detail="Reservation deleted")
