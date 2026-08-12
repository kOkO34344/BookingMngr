from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.deps import DbSession, OrganizationId
from app.models.guest import Guest
from app.schemas.guest import GuestCreate, GuestRead, GuestUpdate

router = APIRouter(prefix="/guests", tags=["guests"])


def _get_or_404(db: DbSession, guest_id: int, organization_id: int) -> Guest:
    guest = db.scalars(
        select(Guest).where(
            Guest.id == guest_id, Guest.organization_id == organization_id
        )
    ).first()
    if guest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")
    return guest


@router.get("", response_model=list[GuestRead])
def list_guests(
    db: DbSession,
    organization_id: OrganizationId,
    search: str | None = Query(default=None, description="Match name, email or phone"),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Guest]:
    query = select(Guest).where(Guest.organization_id == organization_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Guest.full_name.ilike(pattern),
                Guest.email.ilike(pattern),
                Guest.phone.ilike(pattern),
            )
        )
    return list(
        db.scalars(query.order_by(Guest.full_name).limit(limit).offset(offset)).all()
    )


@router.post("", response_model=GuestRead, status_code=status.HTTP_201_CREATED)
def create_guest(
    payload: GuestCreate, db: DbSession, organization_id: OrganizationId
) -> Guest:
    guest = Guest(organization_id=organization_id, **payload.model_dump())
    db.add(guest)
    db.flush()
    db.refresh(guest)
    return guest


@router.get("/{guest_id}", response_model=GuestRead)
def get_guest(guest_id: int, db: DbSession, organization_id: OrganizationId) -> Guest:
    return _get_or_404(db, guest_id, organization_id)


@router.patch("/{guest_id}", response_model=GuestRead)
def update_guest(
    guest_id: int,
    payload: GuestUpdate,
    db: DbSession,
    organization_id: OrganizationId,
) -> Guest:
    guest = _get_or_404(db, guest_id, organization_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(guest, field, value)
    db.flush()
    db.refresh(guest)
    return guest
