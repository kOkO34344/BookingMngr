"""Domain enumerations.

These are stored as native strings (VARCHAR + CHECK-free) rather than PG ENUM
types so that adding a value later is a code change, not a migration.
"""

from enum import StrEnum


class PropertyType(StrEnum):
    HOTEL = "hotel"
    APARTMENT_BUILDING = "apartment_building"
    MIXED = "mixed"


class UnitStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_SERVICE = "out_of_service"


class HousekeepingStatus(StrEnum):
    DIRTY = "dirty"
    CLEANING = "cleaning"
    CLEAN = "clean"
    MAINTENANCE = "maintenance"


class ReservationSource(StrEnum):
    AIRBNB = "airbnb"
    BOOKING = "booking"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class ReservationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_HOUSE = "in_house"
    CHECKED_OUT = "checked_out"
    CANCELED = "canceled"
    NO_SHOW = "no_show"


#: Statuses that still occupy the unit (used for availability + occupancy).
BLOCKING_RESERVATION_STATUSES: frozenset[ReservationStatus] = frozenset(
    {
        ReservationStatus.PENDING,
        ReservationStatus.CONFIRMED,
        ReservationStatus.IN_HOUSE,
        ReservationStatus.CHECKED_OUT,
    }
)


class PaymentMethod(StrEnum):
    AIRBNB_PAYOUT = "airbnb_payout"
    BOOKING_PAYOUT = "booking_payout"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"


class TaskType(StrEnum):
    HOUSEKEEPING_CHECKOUT_CLEAN = "housekeeping_checkout_clean"
    HOUSEKEEPING_STAYOVER_CLEAN = "housekeeping_stayover_clean"
    MAINTENANCE_ISSUE = "maintenance_issue"
    INSPECTION = "inspection"
    OTHER = "other"


class TaskStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PayoutSource(StrEnum):
    AIRBNB = "airbnb"
    BOOKING = "booking"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
