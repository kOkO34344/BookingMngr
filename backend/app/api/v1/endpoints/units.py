"""Units.

Two routers: nested under a property for list/create (the natural collection),
flat for item operations so the frontend can link straight to /units/{id}.
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import Actor, DbSession, OrganizationId
from app.core.logging import log_event
from app.models.property import Property
from app.models.unit import Unit
from app.schemas.common import Message
from app.schemas.unit import UnitCreate, UnitRead, UnitUpdate

property_units_router = APIRouter(prefix="/properties", tags=["units"])
units_router = APIRouter(prefix="/units", tags=["units"])


def _assert_property(db: DbSession, property_id: int, organization_id: int) -> Property:
    prop = db.scalars(
        select(Property).where(
            Property.id == property_id, Property.organization_id == organization_id
        )
    ).first()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    return prop


def _get_unit_or_404(db: DbSession, unit_id: int, organization_id: int) -> Unit:
    unit = db.scalars(
        select(Unit)
        .join(Property, Property.id == Unit.property_id)
        .where(Unit.id == unit_id, Property.organization_id == organization_id)
    ).first()
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")
    return unit


@property_units_router.get("/{property_id}/units", response_model=list[UnitRead])
def list_units(
    property_id: int,
    db: DbSession,
    organization_id: OrganizationId,
    include_archived: bool = Query(default=False),
) -> list[Unit]:
    _assert_property(db, property_id, organization_id)
    query = select(Unit).where(Unit.property_id == property_id)
    if not include_archived:
        query = query.where(Unit.is_archived.is_(False))
    return list(db.scalars(query.order_by(Unit.floor, Unit.name_or_number)).all())


@property_units_router.post(
    "/{property_id}/units", response_model=UnitRead, status_code=status.HTTP_201_CREATED
)
def create_unit(
    property_id: int,
    payload: UnitCreate,
    db: DbSession,
    organization_id: OrganizationId,
) -> Unit:
    _assert_property(db, property_id, organization_id)
    unit = Unit(property_id=property_id, **payload.model_dump())
    db.add(unit)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A unit named '{payload.name_or_number}' already exists in this property",
        ) from exc
    db.refresh(unit)
    return unit


@units_router.get("/{unit_id}", response_model=UnitRead)
def get_unit(unit_id: int, db: DbSession, organization_id: OrganizationId) -> Unit:
    return _get_unit_or_404(db, unit_id, organization_id)


@units_router.patch("/{unit_id}", response_model=UnitRead)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
) -> Unit:
    unit = _get_unit_or_404(db, unit_id, organization_id)
    updates = payload.model_dump(exclude_unset=True)
    previous_hk = unit.housekeeping_status

    for field, value in updates.items():
        setattr(unit, field, value)
    db.flush()

    if "housekeeping_status" in updates and unit.housekeeping_status != previous_hk:
        log_event(
            db,
            entity_type="unit",
            entity_id=unit.id,
            action="housekeeping_status_changed",
            actor=actor,
            organization_id=organization_id,
            changes={
                "housekeeping_status": {"from": previous_hk, "to": unit.housekeeping_status}
            },
        )
    db.refresh(unit)
    return unit


@units_router.delete("/{unit_id}", response_model=Message)
def archive_unit(
    unit_id: int, db: DbSession, organization_id: OrganizationId, actor: Actor
) -> Message:
    unit = _get_unit_or_404(db, unit_id, organization_id)
    unit.is_archived = True
    log_event(
        db,
        entity_type="unit",
        entity_id=unit.id,
        action="archived",
        actor=actor,
        organization_id=organization_id,
    )
    return Message(detail="Unit archived")
