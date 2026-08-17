from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ReservationSource
from app.schemas.reservation import ReservationDetail
from app.schemas.task import TaskDetail


class DailyBoardKpis(BaseModel):
    total_units: int
    occupied_units: int
    occupancy_pct: float
    arrivals_count: int
    departures_count: int
    in_house_count: int
    tasks_total: int
    tasks_completed: int
    tasks_open: int
    units_dirty: int


class PropertyBoard(BaseModel):
    property_id: int
    property_name: str
    arrivals: list[ReservationDetail]
    departures: list[ReservationDetail]
    in_house: list[ReservationDetail]
    tasks: list[TaskDetail]
    kpis: DailyBoardKpis


class DailyBoardResponse(BaseModel):
    date: date
    properties: list[PropertyBoard]
    totals: DailyBoardKpis
    #: Net payout for stays checked out between the 1st and the board's date.
    net_payout_mtd: Decimal
    currency: str


class RevenueBySource(BaseModel):
    source: ReservationSource
    reservations_count: int
    nights: int
    gross_amount: Decimal
    fees_amount: Decimal
    net_payout_amount: Decimal


class PropertyRevenue(BaseModel):
    property_id: int
    property_name: str
    currency: str
    nights: int
    reservations_count: int
    gross_amount: Decimal
    fees_amount: Decimal
    net_payout_amount: Decimal
    by_source: list[RevenueBySource]
    reservations: list[ReservationDetail]


class MonthlyRevenueResponse(BaseModel):
    year: int
    month: int
    period_start: date
    period_end: date
    currency: str
    properties: list[PropertyRevenue]
    total_gross_amount: Decimal
    total_fees_amount: Decimal
    total_net_payout_amount: Decimal
    total_nights: int
    by_source: list[RevenueBySource]
