"""Task domain logic, including housekeeping generation and completion side effects."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status as http_status
from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import diff_fields, log_event
from app.models.enums import (
    HousekeepingStatus,
    ReservationStatus,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from app.models.property import Property
from app.models.reservation import Reservation
from app.models.task import Task
from app.models.unit import Unit
from app.schemas.task import (
    GenerateHousekeepingRequest,
    GenerateHousekeepingResponse,
    TaskCreate,
    TaskDetail,
    TaskUpdate,
)

AUDITED_FIELDS = ("status", "assigned_to", "due_date", "priority", "unit_id")

#: The priority column stores strings, so sort by explicit rank, not alphabetically.
PRIORITY_RANK = case(
    {
        TaskPriority.URGENT.value: 0,
        TaskPriority.HIGH.value: 1,
        TaskPriority.NORMAL.value: 2,
        TaskPriority.LOW.value: 3,
    },
    value=Task.priority,
    else_=4,
)

#: Housekeeping task types that are generated automatically per checkout.
CHECKOUT_TASK_TYPE = TaskType.HOUSEKEEPING_CHECKOUT_CLEAN
STAYOVER_TASK_TYPE = TaskType.HOUSEKEEPING_STAYOVER_CLEAN


def _base_query() -> Select[tuple[Task]]:
    return select(Task).options(
        selectinload(Task.property), selectinload(Task.unit), selectinload(Task.reservation)
    )


def to_detail(task: Task) -> TaskDetail:
    detail = TaskDetail.model_validate(task)
    detail.property_name = task.property.name if task.property else None
    detail.unit_name = task.unit.name_or_number if task.unit else None
    return detail


def get_or_404(db: Session, task_id: int, organization_id: int) -> Task:
    task = db.scalars(
        _base_query()
        .join(Property, Property.id == Task.property_id)
        .where(Task.id == task_id, Property.organization_id == organization_id)
    ).first()
    if task is None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def list_tasks(
    db: Session,
    *,
    organization_id: int,
    due_date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    property_id: int | None = None,
    unit_id: int | None = None,
    task_status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    assigned_to: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[Task], int]:
    filters = [Property.organization_id == organization_id]
    if due_date is not None:
        filters.append(Task.due_date == due_date)
    if from_date is not None:
        filters.append(Task.due_date >= from_date)
    if to_date is not None:
        filters.append(Task.due_date <= to_date)
    if property_id is not None:
        filters.append(Task.property_id == property_id)
    if unit_id is not None:
        filters.append(Task.unit_id == unit_id)
    if task_status is not None:
        filters.append(Task.status == task_status)
    if task_type is not None:
        filters.append(Task.task_type == task_type)
    if assigned_to:
        filters.append(Task.assigned_to.ilike(f"%{assigned_to}%"))

    total = db.scalar(
        select(func.count())
        .select_from(Task)
        .join(Property, Property.id == Task.property_id)
        .where(*filters)
    ) or 0

    rows = (
        db.scalars(
            _base_query()
            .join(Property, Property.id == Task.property_id)
            .where(*filters)
            .order_by(Task.due_date.asc().nulls_last(), PRIORITY_RANK, Task.id.asc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return list(rows), total


def _validate_scope(
    db: Session, *, property_id: int, unit_id: int | None, organization_id: int
) -> None:
    prop = db.scalars(
        select(Property).where(
            Property.id == property_id, Property.organization_id == organization_id
        )
    ).first()
    if prop is None:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown property")
    if unit_id is not None:
        unit = db.scalars(
            select(Unit).where(Unit.id == unit_id, Unit.property_id == property_id)
        ).first()
        if unit is None:
            raise HTTPException(
                http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Unit does not belong to this property",
            )


def create_task(
    db: Session, payload: TaskCreate, *, organization_id: int, actor: str
) -> Task:
    _validate_scope(
        db,
        property_id=payload.property_id,
        unit_id=payload.unit_id,
        organization_id=organization_id,
    )
    task = Task(**payload.model_dump())
    if task.status is TaskStatus.COMPLETED and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)
    db.add(task)
    db.flush()
    log_event(
        db,
        entity_type="task",
        entity_id=task.id,
        action="created",
        actor=actor,
        organization_id=organization_id,
        changes={"task_type": task.task_type, "status": task.status, "due_date": task.due_date},
    )
    db.refresh(task)
    return task


def update_task(
    db: Session, task: Task, payload: TaskUpdate, *, organization_id: int, actor: str
) -> Task:
    updates = payload.model_dump(exclude_unset=True)
    before = {field: getattr(task, field) for field in AUDITED_FIELDS}

    if "unit_id" in updates:
        _validate_scope(
            db,
            property_id=task.property_id,
            unit_id=updates["unit_id"],
            organization_id=organization_id,
        )

    was_completed = task.status is TaskStatus.COMPLETED
    for field, value in updates.items():
        setattr(task, field, value)

    now_completed = task.status is TaskStatus.COMPLETED
    if now_completed and not was_completed:
        task.completed_at = datetime.now(timezone.utc)
        _apply_completion_side_effects(
            db, task, organization_id=organization_id, actor=actor
        )
    elif not now_completed and was_completed:
        task.completed_at = None

    db.flush()

    after = {field: getattr(task, field) for field in AUDITED_FIELDS}
    changes = diff_fields(before, after)
    if changes:
        action = "completed" if (now_completed and not was_completed) else "updated"
        log_event(
            db,
            entity_type="task",
            entity_id=task.id,
            action=action,
            actor=actor,
            organization_id=organization_id,
            changes=changes,
        )
    db.refresh(task)
    return task


def _apply_completion_side_effects(
    db: Session, task: Task, *, organization_id: int, actor: str
) -> None:
    """Completing a task can move the unit's housekeeping status."""
    if task.unit_id is None or task.changes_room_status_to is None:
        return
    unit = db.get(Unit, task.unit_id)
    if unit is None or unit.housekeeping_status == task.changes_room_status_to:
        return
    previous = unit.housekeeping_status
    unit.housekeeping_status = task.changes_room_status_to
    log_event(
        db,
        entity_type="unit",
        entity_id=unit.id,
        action="housekeeping_status_changed",
        actor=actor,
        organization_id=organization_id,
        changes={
            "housekeeping_status": {"from": previous, "to": unit.housekeeping_status},
            "via_task_id": task.id,
        },
    )


def generate_housekeeping(
    db: Session,
    payload: GenerateHousekeepingRequest,
    *,
    organization_id: int,
    actor: str,
) -> GenerateHousekeepingResponse:
    """Create checkout-clean tasks for every departure on `payload.date`.

    Idempotent: re-running for the same day will not duplicate tasks.
    Units with a departure are flipped to `dirty`.
    """
    target = payload.date

    departures_query = (
        select(Reservation)
        .join(Property, Property.id == Reservation.property_id)
        .options(selectinload(Reservation.unit))
        .where(
            Property.organization_id == organization_id,
            Reservation.check_out_date == target,
            Reservation.status.notin_(
                [ReservationStatus.CANCELED, ReservationStatus.NO_SHOW]
            ),
        )
    )
    if payload.property_id is not None:
        departures_query = departures_query.where(
            Reservation.property_id == payload.property_id
        )
    departures = list(db.scalars(departures_query).unique().all())

    jobs: list[tuple[Reservation, TaskType]] = [(r, CHECKOUT_TASK_TYPE) for r in departures]

    if payload.include_stayovers:
        stayover_query = (
            select(Reservation)
            .join(Property, Property.id == Reservation.property_id)
            .options(selectinload(Reservation.unit))
            .where(
                Property.organization_id == organization_id,
                Reservation.check_in_date < target,
                Reservation.check_out_date > target,
                Reservation.status.notin_(
                    [ReservationStatus.CANCELED, ReservationStatus.NO_SHOW]
                ),
            )
        )
        if payload.property_id is not None:
            stayover_query = stayover_query.where(
                Reservation.property_id == payload.property_id
            )
        jobs += [(r, STAYOVER_TASK_TYPE) for r in db.scalars(stayover_query).unique().all()]

    created: list[Task] = []
    skipped = 0
    units_marked_dirty: list[int] = []

    for reservation, job_type in jobs:
        existing = db.scalars(
            select(Task).where(
                Task.reservation_id == reservation.id,
                Task.task_type == job_type,
                Task.due_date == target,
                Task.status != TaskStatus.CANCELED,
            )
        ).first()
        if existing is not None:
            skipped += 1
            continue

        unit = reservation.unit
        task = Task(
            property_id=reservation.property_id,
            unit_id=reservation.unit_id,
            reservation_id=reservation.id,
            task_type=job_type,
            status=TaskStatus.SCHEDULED,
            priority=TaskPriority.HIGH
            if job_type is CHECKOUT_TASK_TYPE
            else TaskPriority.NORMAL,
            assigned_to=payload.assigned_to,
            estimated_duration_minutes=unit.cleaning_duration_minutes if unit else None,
            due_date=target,
            description=(
                f"Checkout clean for {unit.name_or_number if unit else 'unit'} "
                f"after {reservation.display_guest_name}"
                if job_type is CHECKOUT_TASK_TYPE
                else f"Stayover clean for {unit.name_or_number if unit else 'unit'}"
            ),
            changes_room_status_to=HousekeepingStatus.CLEAN,
        )
        db.add(task)
        created.append(task)

        if job_type is CHECKOUT_TASK_TYPE and unit is not None:
            if unit.housekeeping_status is not HousekeepingStatus.MAINTENANCE:
                if unit.housekeeping_status is not HousekeepingStatus.DIRTY:
                    unit.housekeeping_status = HousekeepingStatus.DIRTY
                    units_marked_dirty.append(unit.id)

    db.flush()

    for task in created:
        log_event(
            db,
            entity_type="task",
            entity_id=task.id,
            action="generated",
            actor=actor,
            organization_id=organization_id,
            changes={"task_type": task.task_type, "reservation_id": task.reservation_id},
        )
    for unit_id in units_marked_dirty:
        log_event(
            db,
            entity_type="unit",
            entity_id=unit_id,
            action="housekeeping_status_changed",
            actor=actor,
            organization_id=organization_id,
            changes={"housekeeping_status": {"to": HousekeepingStatus.DIRTY.value}},
        )

    for task in created:
        db.refresh(task)

    return GenerateHousekeepingResponse(
        date=target,
        created=[to_detail(t) for t in created],
        skipped_existing=skipped,
        units_marked_dirty=units_marked_dirty,
    )
