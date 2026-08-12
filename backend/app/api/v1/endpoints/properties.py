from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import Actor, DbSession, OrganizationId
from app.core.logging import log_event
from app.models.property import Property
from app.models.unit import Unit
from app.schemas.common import Message
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyWithStats

router = APIRouter(prefix="/properties", tags=["properties"])


def _get_or_404(db: DbSession, property_id: int, organization_id: int) -> Property:
    prop = db.scalars(
        select(Property).where(
            Property.id == property_id, Property.organization_id == organization_id
        )
    ).first()
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    return prop


def _with_stats(db: DbSession, prop: Property) -> PropertyWithStats:
    units_count = db.scalar(
        select(func.count())
        .select_from(Unit)
        .where(Unit.property_id == prop.id, Unit.is_archived.is_(False))
    )
    result = PropertyWithStats.model_validate(prop)
    result.units_count = units_count or 0
    return result


@router.get("", response_model=list[PropertyWithStats])
def list_properties(
    db: DbSession,
    organization_id: OrganizationId,
    include_archived: bool = Query(default=False),
) -> list[PropertyWithStats]:
    query = select(Property).where(Property.organization_id == organization_id)
    if not include_archived:
        query = query.where(Property.is_archived.is_(False))
    props = db.scalars(query.order_by(Property.name)).all()
    return [_with_stats(db, p) for p in props]


@router.post("", response_model=PropertyWithStats, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate, db: DbSession, organization_id: OrganizationId
) -> PropertyWithStats:
    prop = Property(organization_id=organization_id, **payload.model_dump())
    db.add(prop)
    db.flush()
    db.refresh(prop)
    return _with_stats(db, prop)


@router.get("/{property_id}", response_model=PropertyWithStats)
def get_property(
    property_id: int, db: DbSession, organization_id: OrganizationId
) -> PropertyWithStats:
    return _with_stats(db, _get_or_404(db, property_id, organization_id))


@router.patch("/{property_id}", response_model=PropertyWithStats)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: DbSession,
    organization_id: OrganizationId,
) -> PropertyWithStats:
    prop = _get_or_404(db, property_id, organization_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.flush()
    db.refresh(prop)
    return _with_stats(db, prop)


@router.delete("/{property_id}", response_model=Message)
def archive_property(
    property_id: int,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
    hard_delete: bool = Query(
        default=False, description="Permanently delete. Fails if reservations exist."
    ),
) -> Message:
    """Archive by default — reservation history must survive."""
    prop = _get_or_404(db, property_id, organization_id)

    if hard_delete:
        if prop.reservations:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Property has reservations; archive it instead of deleting.",
            )
        db.delete(prop)
        log_event(
            db,
            entity_type="property",
            entity_id=property_id,
            action="deleted",
            actor=actor,
            organization_id=organization_id,
        )
        return Message(detail="Property deleted")

    prop.is_archived = True
    log_event(
        db,
        entity_type="property",
        entity_id=property_id,
        action="archived",
        actor=actor,
        organization_id=organization_id,
    )
    return Message(detail="Property archived")
