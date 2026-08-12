"""Reservation domain logic: validation, overlap checks, calendar shaping."""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status as http_status
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.logging import diff_fields, log_event
from app.models.enums import BLOCKING_RESERVATION_STATUSES, ReservationSource, ReservationStatus
from app.models.property import Property
from app.models.reservation import Reservation
from app.models.unit import Unit
from app.schemas.reservation import (
    CalendarBlock,
    CalendarResponse,
    CalendarUnitRow,
    ReservationCreate,
    ReservationDetail,
    ReservationUpdate,
)

ONE_DAY = timedelta(days=1)

#: Postgres exclusion constraint guarding against double bookings. Only present
#: on Postgres; on SQLite the service-level check is the only guard.
OVERLAP_CONSTRAINT = "ex_reservations_no_overlap"

#: Fields whose changes are interesting enough to write to the audit trail.
AUDITED_FIELDS = (
    "status",
    "check_in_date",
    "check_out_date",
    "unit_id",
    "net_payout_amount",
    "payment_status",
)


def _base_query() -> Select[tuple[Reservation]]:
    return select(Reservation).options(
        selectinload(Reservation.property),
        selectinload(Reservation.unit),
        selectinload(Reservation.guest),
    )


def to_detail(reservation: Reservation) -> ReservationDetail:
    detail = ReservationDetail.model_validate(reservation)
    detail.property_name = reservation.property.name if reservation.property else None
    detail.unit_name = reservation.unit.name_or_number if reservation.unit else None
    detail.guest_display_name = reservation.display_guest_name
    return detail


def get_or_404(db: Session, reservation_id: int, organization_id: int) -> Reservation:
    reservation = db.scalars(
        _base_query()
        .join(Property, Property.id == Reservation.property_id)
        .where(Reservation.id == reservation_id, Property.organization_id == organization_id)
    ).first()
    if reservation is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Reservation not found")
    return reservation


def list_reservations(
    db: Session,
    *,
    organization_id: int,
    property_id: int | None = None,
    unit_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    reservation_status: ReservationStatus | None = None,
    source: ReservationSource | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Reservation], int]:
    filters = [Property.organization_id == organization_id]

    if property_id is not None:
        filters.append(Reservation.property_id == property_id)
    if unit_id is not None:
        filters.append(Reservation.unit_id == unit_id)
    # Overlap semantics: any stay that intersects [from_date, to_date].
    if from_date is not None:
        filters.append(Reservation.check_out_date > from_date)
    if to_date is not None:
        filters.append(Reservation.check_in_date <= to_date)
    if reservation_status is not None:
        filters.append(Reservation.status == reservation_status)
    if source is not None:
        filters.append(Reservation.source == source)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Reservation.guest_name.ilike(pattern),
                Reservation.source_reference.ilike(pattern),
                Reservation.notes.ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .join(Property, Property.id == Reservation.property_id)
        .where(*filters)
    ) or 0

    rows = (
        db.scalars(
            _base_query()
            .join(Property, Property.id == Reservation.property_id)
            .where(*filters)
            .order_by(Reservation.check_in_date.desc(), Reservation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return list(rows), total


def find_overlapping(
    db: Session,
    *,
    unit_id: int,
    check_in: date,
    check_out: date,
    exclude_id: int | None = None,
) -> Reservation | None:
    """Same-unit double booking check. Check-out day is free for the next guest."""
    query = select(Reservation).where(
        Reservation.unit_id == unit_id,
        Reservation.status.in_(list(BLOCKING_RESERVATION_STATUSES)),
        and_(Reservation.check_in_date < check_out, Reservation.check_out_date > check_in),
    )
    if exclude_id is not None:
        query = query.where(Reservation.id != exclude_id)
    return db.scalars(query).first()


def _flush_or_conflict(db: Session) -> None:
    """Flush, translating the overlap constraint into the same 409 as the pre-check.

    `find_overlapping` reads before writing, so two concurrent bookings can both
    see a free unit. Postgres catches the loser via `ex_reservations_no_overlap`
    (see the migration of the same name); without this the caller would get a
    500 for what is an ordinary conflict.
    """
    try:
        db.flush()
    except IntegrityError as exc:
        if OVERLAP_CONSTRAINT not in str(exc.orig):
            raise
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            "Unit was booked for those dates by a concurrent request",
        ) from exc


def _validate_unit(db: Session, *, property_id: int, unit_id: int, organization_id: int) -> Unit:
    unit = db.scalars(
        select(Unit)
        .join(Property, Property.id == Unit.property_id)
        .where(
            Unit.id == unit_id,
            Unit.property_id == property_id,
            Property.organization_id == organization_id,
        )
    ).first()
    if unit is None:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Unit does not exist or does not belong to this property",
        )
    return unit


def create_reservation(
    db: Session, payload: ReservationCreate, *, organization_id: int, actor: str
) -> Reservation:
    _validate_unit(
        db,
        property_id=payload.property_id,
        unit_id=payload.unit_id,
        organization_id=organization_id,
    )
    clash = find_overlapping(
        db,
        unit_id=payload.unit_id,
        check_in=payload.check_in_date,
        check_out=payload.check_out_date,
    )
    if clash is not None:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            f"Unit is already booked by reservation #{clash.id} "
            f"({clash.check_in_date} → {clash.check_out_date})",
        )

    data = payload.model_dump()
    if data.get("net_payout_amount") is None:
        data["net_payout_amount"] = Decimal(data["gross_amount"]) - Decimal(data["fees_amount"])
    reservation = Reservation(**data)
    db.add(reservation)
    _flush_or_conflict(db)

    log_event(
        db,
        entity_type="reservation",
        entity_id=reservation.id,
        action="created",
        actor=actor,
        organization_id=organization_id,
        changes={
            "status": reservation.status,
            "source": reservation.source,
            "check_in_date": reservation.check_in_date,
            "check_out_date": reservation.check_out_date,
        },
    )
    db.refresh(reservation)
    return reservation


def update_reservation(
    db: Session,
    reservation: Reservation,
    payload: ReservationUpdate,
    *,
    organization_id: int,
    actor: str,
) -> Reservation:
    updates = payload.model_dump(exclude_unset=True)
    before = {field: getattr(reservation, field) for field in AUDITED_FIELDS}

    new_unit_id = updates.get("unit_id", reservation.unit_id)
    new_check_in = updates.get("check_in_date", reservation.check_in_date)
    new_check_out = updates.get("check_out_date", reservation.check_out_date)
    if new_check_out <= new_check_in:
        raise HTTPException(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "check_out_date must be after check_in_date",
        )
    if "unit_id" in updates:
        _validate_unit(
            db,
            property_id=reservation.property_id,
            unit_id=new_unit_id,
            organization_id=organization_id,
        )

    new_status = updates.get("status", reservation.status)
    dates_or_unit_changed = (
        new_unit_id != reservation.unit_id
        or new_check_in != reservation.check_in_date
        or new_check_out != reservation.check_out_date
    )
    # Reopening a canceled booking claims the unit just as surely as moving its
    # dates does, so it needs the same check.
    became_blocking = (
        new_status in BLOCKING_RESERVATION_STATUSES
        and reservation.status not in BLOCKING_RESERVATION_STATUSES
    )
    if new_status in BLOCKING_RESERVATION_STATUSES and (
        dates_or_unit_changed or became_blocking
    ):
        clash = find_overlapping(
            db,
            unit_id=new_unit_id,
            check_in=new_check_in,
            check_out=new_check_out,
            exclude_id=reservation.id,
        )
        if clash is not None:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Unit is already booked by reservation #{clash.id}",
            )

    for field, value in updates.items():
        setattr(reservation, field, value)

    # Keep the derived payout consistent when only the money fields moved.
    if ("gross_amount" in updates or "fees_amount" in updates) and "net_payout_amount" not in updates:
        reservation.net_payout_amount = reservation.gross_amount - reservation.fees_amount

    _flush_or_conflict(db)

    after = {field: getattr(reservation, field) for field in AUDITED_FIELDS}
    changes = diff_fields(before, after)
    if changes:
        action = "status_changed" if "status" in changes else "updated"
        log_event(
            db,
            entity_type="reservation",
            entity_id=reservation.id,
            action=action,
            actor=actor,
            organization_id=organization_id,
            changes=changes,
        )
    db.refresh(reservation)
    return reservation


def daily_reservations(
    db: Session, *, target_date: date, organization_id: int, property_id: int | None = None
) -> tuple[list[Reservation], list[Reservation], list[Reservation]]:
    """Return (arrivals, departures, in_house) for a single day."""
    query = (
        _base_query()
        .join(Property, Property.id == Reservation.property_id)
        .where(
            Property.organization_id == organization_id,
            Reservation.status.notin_(
                [ReservationStatus.CANCELED, ReservationStatus.NO_SHOW]
            ),
            Reservation.check_in_date <= target_date,
            Reservation.check_out_date >= target_date,
        )
    )
    if property_id is not None:
        query = query.where(Reservation.property_id == property_id)

    rows = list(db.scalars(query.order_by(Reservation.unit_id)).unique().all())
    arrivals = [r for r in rows if r.check_in_date == target_date]
    departures = [r for r in rows if r.check_out_date == target_date]
    in_house = [
        r for r in rows if r.check_in_date < target_date < r.check_out_date
    ]
    return arrivals, departures, in_house


def build_calendar(
    db: Session, *, property_id: int, year: int, month: int, organization_id: int
) -> CalendarResponse:
    prop = db.scalars(
        select(Property).where(
            Property.id == property_id, Property.organization_id == organization_id
        )
    ).first()
    if prop is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Property not found")

    days_in_month = calendar_mod.monthrange(year, month)[1]
    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)

    units = list(
        db.scalars(
            select(Unit)
            .where(Unit.property_id == property_id, Unit.is_archived.is_(False))
            .order_by(Unit.floor, Unit.name_or_number)
        ).all()
    )

    reservations = list(
        db.scalars(
            _base_query().where(
                Reservation.property_id == property_id,
                Reservation.status.notin_([ReservationStatus.CANCELED]),
                Reservation.check_in_date <= last_day,
                Reservation.check_out_date > first_day,
            )
        ).unique().all()
    )

    by_unit: dict[int, list[Reservation]] = {}
    for reservation in reservations:
        by_unit.setdefault(reservation.unit_id, []).append(reservation)

    rows: list[CalendarUnitRow] = []
    for unit in units:
        blocks: list[CalendarBlock] = []
        for reservation in sorted(by_unit.get(unit.id, []), key=lambda r: r.check_in_date):
            visible_start = max(reservation.check_in_date, first_day)
            visible_end = min(reservation.check_out_date, last_day + ONE_DAY)
            span = (visible_end - visible_start).days
            if span <= 0:
                continue
            blocks.append(
                CalendarBlock(
                    reservation_id=reservation.id,
                    unit_id=unit.id,
                    guest_name=reservation.display_guest_name,
                    source=reservation.source,
                    status=reservation.status,
                    check_in_date=reservation.check_in_date,
                    check_out_date=reservation.check_out_date,
                    nights=reservation.nights,
                    start_offset=(visible_start - first_day).days,
                    span_days=span,
                    continues_before=reservation.check_in_date < first_day,
                    continues_after=reservation.check_out_date > last_day + ONE_DAY,
                )
            )
        rows.append(
            CalendarUnitRow(
                unit_id=unit.id,
                unit_name=unit.name_or_number,
                housekeeping_status=unit.housekeeping_status.value,
                blocks=blocks,
            )
        )

    return CalendarResponse(
        property_id=property_id,
        year=year,
        month=month,
        days_in_month=days_in_month,
        first_day=first_day,
        units=rows,
    )
