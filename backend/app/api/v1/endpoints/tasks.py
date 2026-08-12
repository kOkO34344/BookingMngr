from datetime import date

from fastapi import APIRouter, Query, status

from app.api.deps import Actor, DbSession, OrganizationId
from app.core.logging import log_event
from app.models.enums import TaskStatus, TaskType
from app.schemas.common import Message, Page
from app.schemas.task import (
    GenerateHousekeepingRequest,
    GenerateHousekeepingResponse,
    TaskCreate,
    TaskDetail,
    TaskUpdate,
)
from app.services import tasks as service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskDetail])
def list_tasks(
    db: DbSession,
    organization_id: OrganizationId,
    date_: date | None = Query(default=None, alias="date", description="Exact due date"),
    from_date: date | None = None,
    to_date: date | None = None,
    property_id: int | None = None,
    unit_id: int | None = None,
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    task_type: TaskType | None = None,
    assigned_to: str | None = None,
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
) -> Page[TaskDetail]:
    rows, total = service.list_tasks(
        db,
        organization_id=organization_id,
        due_date=date_,
        from_date=from_date,
        to_date=to_date,
        property_id=property_id,
        unit_id=unit_id,
        task_status=task_status,
        task_type=task_type,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    return Page[TaskDetail](
        items=[service.to_detail(t) for t in rows], total=total, limit=limit, offset=offset
    )


@router.post("", response_model=TaskDetail, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate, db: DbSession, organization_id: OrganizationId, actor: Actor
) -> TaskDetail:
    task = service.create_task(db, payload, organization_id=organization_id, actor=actor)
    return service.to_detail(task)


@router.post(
    "/generate-housekeeping",
    response_model=GenerateHousekeepingResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_housekeeping(
    payload: GenerateHousekeepingRequest,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
) -> GenerateHousekeepingResponse:
    """Create checkout-clean tasks for the day's departures and mark units dirty.

    Safe to run repeatedly — existing tasks for the same reservation and day are
    skipped rather than duplicated.
    """
    return service.generate_housekeeping(
        db, payload, organization_id=organization_id, actor=actor
    )


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: int, db: DbSession, organization_id: OrganizationId) -> TaskDetail:
    return service.to_detail(service.get_or_404(db, task_id, organization_id))


@router.patch("/{task_id}", response_model=TaskDetail)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: DbSession,
    organization_id: OrganizationId,
    actor: Actor,
) -> TaskDetail:
    task = service.get_or_404(db, task_id, organization_id)
    updated = service.update_task(
        db, task, payload, organization_id=organization_id, actor=actor
    )
    return service.to_detail(updated)


@router.delete("/{task_id}", response_model=Message)
def delete_task(
    task_id: int, db: DbSession, organization_id: OrganizationId, actor: Actor
) -> Message:
    task = service.get_or_404(db, task_id, organization_id)
    log_event(
        db,
        entity_type="task",
        entity_id=task.id,
        action="deleted",
        actor=actor,
        organization_id=organization_id,
    )
    db.delete(task)
    return Message(detail="Task deleted")
