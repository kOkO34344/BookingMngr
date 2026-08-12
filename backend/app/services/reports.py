"""Aggregations behind /reports: the morning board and monthly revenue."""

from __future__ import annotations

import calendar as calendar_mod
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.enums import (
    HousekeepingStatus,
    ReservationSource,
    ReservationStatus,
    TaskStatus,
    UnitStatus,
)
from app.models.property import Property
from app.models.reservation import Reservation
from app.models.unit import Unit
from app.schemas.report import (
    DailyBoardKpis,
    DailyBoardResponse,
    MonthlyRevenueResponse,
    PropertyBoard,
    PropertyRevenue,
    RevenueBySource,
)
from app.services import reservations as reservation_service
from app.services import tasks as task_service

#: Reservation statuses that count as real revenue.
REVENUE_STATUSES = (
    ReservationStatus.CONFIRMED,
    ReservationStatus.IN_HOUSE,
    ReservationStatus.CHECKED_OUT,
)

ZERO = Decimal("0")


def _empty_kpis() -> DailyBoardKpis:
    return DailyBoardKpis(
        total_units=0,
        occupied_units=0,
        occupancy_pct=0.0,
        arrivals_count=0,
        departures_count=0,
        in_house_count=0,
        tasks_total=0,
        tasks_completed=0,
        tasks_open=0,
        units_dirty=0,
    )


def daily_board(
    db: Session,
    *,
    target_date: date,
    organization_id: int,
    property_id: int | None = None,
) -> DailyBoardResponse:
    props_query = select(Property).where(
        Property.organization_id == organization_id, Property.is_archived.is_(False)
    )
    if property_id is not None:
        props_query = props_query.where(Property.id == property_id)
    properties = list(db.scalars(props_query.order_by(Property.name)).all())

    arrivals, departures, in_house = reservation_service.daily_reservations(
        db, target_date=target_date, organization_id=organization_id, property_id=property_id
    )
    all_tasks, _ = task_service.list_tasks(
        db,
        organization_id=organization_id,
        due_date=target_date,
        property_id=property_id,
        limit=1000,
    )

    units = list(
        db.scalars(
            select(Unit)
            .join(Property, Property.id == Unit.property_id)
            .where(
                Property.organization_id == organization_id,
                Unit.is_archived.is_(False),
                Unit.status == UnitStatus.ACTIVE,
                *( [Unit.property_id == property_id] if property_id is not None else [] ),
            )
        ).all()
    )

    boards: list[PropertyBoard] = []
    totals = _empty_kpis()

    for prop in properties:
        p_arrivals = [r for r in arrivals if r.property_id == prop.id]
        p_departures = [r for r in departures if r.property_id == prop.id]
        p_in_house = [r for r in in_house if r.property_id == prop.id]
        p_tasks = [t for t in all_tasks if t.property_id == prop.id]
        p_units = [u for u in units if u.property_id == prop.id]

        # A unit is occupied tonight if someone arrives today or is staying over.
        occupied_unit_ids = {r.unit_id for r in p_arrivals} | {r.unit_id for r in p_in_house}
        total_units = len(p_units)
        occupied = len(occupied_unit_ids)
        completed = sum(1 for t in p_tasks if t.status is TaskStatus.COMPLETED)
        canceled = sum(1 for t in p_tasks if t.status is TaskStatus.CANCELED)

        kpis = DailyBoardKpis(
            total_units=total_units,
            occupied_units=occupied,
            occupancy_pct=round(occupied / total_units * 100, 1) if total_units else 0.0,
            arrivals_count=len(p_arrivals),
            departures_count=len(p_departures),
            in_house_count=len(p_in_house),
            tasks_total=len(p_tasks),
            tasks_completed=completed,
            tasks_open=len(p_tasks) - completed - canceled,
            units_dirty=sum(
                1 for u in p_units if u.housekeeping_status is HousekeepingStatus.DIRTY
            ),
        )

        boards.append(
            PropertyBoard(
                property_id=prop.id,
                property_name=prop.name,
                arrivals=[reservation_service.to_detail(r) for r in p_arrivals],
                departures=[reservation_service.to_detail(r) for r in p_departures],
                in_house=[reservation_service.to_detail(r) for r in p_in_house],
                tasks=[task_service.to_detail(t) for t in p_tasks],
                kpis=kpis,
            )
        )

        totals.total_units += kpis.total_units
        totals.occupied_units += kpis.occupied_units
        totals.arrivals_count += kpis.arrivals_count
        totals.departures_count += kpis.departures_count
        totals.in_house_count += kpis.in_house_count
        totals.tasks_total += kpis.tasks_total
        totals.tasks_completed += kpis.tasks_completed
        totals.tasks_open += kpis.tasks_open
        totals.units_dirty += kpis.units_dirty

    totals.occupancy_pct = (
        round(totals.occupied_units / totals.total_units * 100, 1)
        if totals.total_units
        else 0.0
    )

    return DailyBoardResponse(date=target_date, properties=boards, totals=totals)


def monthly_revenue(
    db: Session,
    *,
    year: int,
    month: int,
    organization_id: int,
    property_id: int | None = None,
) -> MonthlyRevenueResponse:
    """Revenue for a month, attributed by check-out date.

    Check-out is when the stay is finished and the payout is (or becomes) real,
    which matches how the owner reconciles Airbnb/Booking statements. Switching
    to a nightly accrual later means changing only this function.
    """
    period_start = date(year, month, 1)
    period_end = date(year, month, calendar_mod.monthrange(year, month)[1])

    query = (
        select(Reservation)
        .join(Property, Property.id == Reservation.property_id)
        .options(
            selectinload(Reservation.property),
            selectinload(Reservation.unit),
            selectinload(Reservation.guest),
        )
        .where(
            Property.organization_id == organization_id,
            Reservation.status.in_(list(REVENUE_STATUSES)),
            Reservation.check_out_date >= period_start,
            Reservation.check_out_date <= period_end,
        )
    )
    if property_id is not None:
        query = query.where(Reservation.property_id == property_id)

    rows = list(db.scalars(query.order_by(Reservation.check_out_date)).unique().all())

    by_property: dict[int, list[Reservation]] = {}
    for reservation in rows:
        by_property.setdefault(reservation.property_id, []).append(reservation)

    properties: list[PropertyRevenue] = []
    for prop_id, prop_rows in by_property.items():
        prop = prop_rows[0].property
        properties.append(
            PropertyRevenue(
                property_id=prop_id,
                property_name=prop.name if prop else f"Property {prop_id}",
                currency=prop_rows[0].currency,
                nights=sum(r.nights for r in prop_rows),
                reservations_count=len(prop_rows),
                gross_amount=sum((r.gross_amount for r in prop_rows), ZERO),
                fees_amount=sum((r.fees_amount for r in prop_rows), ZERO),
                net_payout_amount=sum((r.net_payout_amount for r in prop_rows), ZERO),
                by_source=_group_by_source(prop_rows),
                reservations=[reservation_service.to_detail(r) for r in prop_rows],
            )
        )
    properties.sort(key=lambda p: p.property_name)

    return MonthlyRevenueResponse(
        year=year,
        month=month,
        period_start=period_start,
        period_end=period_end,
        currency=rows[0].currency if rows else settings.default_currency,
        properties=properties,
        total_gross_amount=sum((r.gross_amount for r in rows), ZERO),
        total_fees_amount=sum((r.fees_amount for r in rows), ZERO),
        total_net_payout_amount=sum((r.net_payout_amount for r in rows), ZERO),
        total_nights=sum(r.nights for r in rows),
        by_source=_group_by_source(rows),
    )


def _group_by_source(rows: list[Reservation]) -> list[RevenueBySource]:
    buckets: dict[ReservationSource, list[Reservation]] = {}
    for reservation in rows:
        buckets.setdefault(reservation.source, []).append(reservation)
    return sorted(
        (
            RevenueBySource(
                source=source,
                reservations_count=len(items),
                nights=sum(r.nights for r in items),
                gross_amount=sum((r.gross_amount for r in items), ZERO),
                fees_amount=sum((r.fees_amount for r in items), ZERO),
                net_payout_amount=sum((r.net_payout_amount for r in items), ZERO),
            )
            for source, items in buckets.items()
        ),
        key=lambda b: b.net_payout_amount,
        reverse=True,
    )


def month_to_date_net(
    db: Session, *, organization_id: int, today: date, property_id: int | None = None
) -> Decimal:
    """Small KPI helper for the dashboard header."""
    period_start = date(today.year, today.month, 1)
    query = (
        select(func.coalesce(func.sum(Reservation.net_payout_amount), 0))
        .select_from(Reservation)
        .join(Property, Property.id == Reservation.property_id)
        .where(
            Property.organization_id == organization_id,
            Reservation.status.in_(list(REVENUE_STATUSES)),
            Reservation.check_out_date >= period_start,
            Reservation.check_out_date <= today,
        )
    )
    if property_id is not None:
        query = query.where(Reservation.property_id == property_id)
    return Decimal(db.scalar(query) or 0)
