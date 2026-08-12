from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DbSession, OrganizationId
from app.schemas.report import DailyBoardResponse, MonthlyRevenueResponse
from app.services import reports as service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-board", response_model=DailyBoardResponse)
def daily_board(
    db: DbSession,
    organization_id: OrganizationId,
    date_: date = Query(default_factory=date.today, alias="date"),
    property_id: int | None = None,
) -> DailyBoardResponse:
    """Morning board: arrivals, departures, in-house stays, tasks and KPIs."""
    return service.daily_board(
        db, target_date=date_, organization_id=organization_id, property_id=property_id
    )


@router.get("/monthly-revenue", response_model=MonthlyRevenueResponse)
def monthly_revenue(
    db: DbSession,
    organization_id: OrganizationId,
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    property_id: int | None = None,
) -> MonthlyRevenueResponse:
    """Net payout totals per property, broken down by channel.

    Revenue is attributed to the month a stay checks out in.
    """
    return service.monthly_revenue(
        db, year=year, month=month, organization_id=organization_id, property_id=property_id
    )
