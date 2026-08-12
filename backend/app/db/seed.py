"""Demo data so the dashboard has something to show.

Run: python -m app.db.seed
Idempotent-ish: it skips seeding if properties already exist.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, logger
from app.db.init_db import ensure_owner, require_schema
from app.db.session import SessionLocal
from app.models.enums import (
    HousekeepingStatus,
    PaymentMethod,
    PaymentStatus,
    PropertyType,
    ReservationSource,
    ReservationStatus,
    TaskPriority,
    TaskStatus,
    TaskType,
    UnitStatus,
)
from app.models.guest import Guest
from app.models.property import Property
from app.models.reservation import Reservation
from app.models.task import Task
from app.models.unit import Unit

FIRST_NAMES = ["Maria", "Ivan", "Sofia", "Luca", "Emma", "Noah", "Ana", "Tom", "Elena", "Jack"]
LAST_NAMES = ["Petrova", "Dimitrov", "Rossi", "Novak", "Smith", "Kovacs", "Weber", "Silva"]

SOURCE_WEIGHTS = [
    (ReservationSource.AIRBNB, 0.4),
    (ReservationSource.BOOKING, 0.3),
    (ReservationSource.PHONE, 0.12),
    (ReservationSource.WHATSAPP, 0.1),
    (ReservationSource.EMAIL, 0.08),
]

PAYMENT_BY_SOURCE = {
    ReservationSource.AIRBNB: PaymentMethod.AIRBNB_PAYOUT,
    ReservationSource.BOOKING: PaymentMethod.BOOKING_PAYOUT,
    ReservationSource.PHONE: PaymentMethod.CASH,
    ReservationSource.WHATSAPP: PaymentMethod.CASH,
    ReservationSource.EMAIL: PaymentMethod.BANK_TRANSFER,
}

FEE_RATE = {
    ReservationSource.AIRBNB: Decimal("0.15"),
    ReservationSource.BOOKING: Decimal("0.18"),
    ReservationSource.PHONE: Decimal("0"),
    ReservationSource.WHATSAPP: Decimal("0"),
    ReservationSource.EMAIL: Decimal("0"),
}


def seed(db: Session, organization_id: int) -> None:
    if db.scalars(select(Property).limit(1)).first() is not None:
        logger.info("Properties already exist — skipping seed.")
        return

    random.seed(7)
    today = date.today()

    seaside = Property(
        organization_id=organization_id,
        name="Seaside Hotel",
        type=PropertyType.HOTEL,
        address="12 Marina Blvd",
        city="Varna",
        country="Bulgaria",
        timezone="Europe/Sofia",
        notes="18 rooms, reception staffed 08:00–20:00.",
    )
    central = Property(
        organization_id=organization_id,
        name="Central Apartments",
        type=PropertyType.APARTMENT_BUILDING,
        address="5 Vitosha St",
        city="Sofia",
        country="Bulgaria",
        timezone="Europe/Sofia",
        notes="Self check-in with keypad codes.",
    )
    db.add_all([seaside, central])
    db.flush()

    units: list[Unit] = []
    for floor in range(1, 4):
        for number in range(1, 5):
            units.append(
                Unit(
                    property_id=seaside.id,
                    name_or_number=f"{floor}0{number}",
                    unit_type="Double room" if number % 2 else "Twin room",
                    capacity=2 if number % 2 else 3,
                    base_price=Decimal("85.00") + floor * 5,
                    cleaning_duration_minutes=45,
                    status=UnitStatus.ACTIVE,
                    housekeeping_status=HousekeepingStatus.CLEAN,
                    floor=str(floor),
                )
            )
    for idx, name in enumerate(["A1", "A2", "B1", "B2", "Studio C"], start=1):
        units.append(
            Unit(
                property_id=central.id,
                name_or_number=name,
                unit_type="Studio" if "Studio" in name else "One-bedroom",
                capacity=2 + (idx % 3),
                base_price=Decimal("70.00") + idx * 4,
                cleaning_duration_minutes=75,
                status=UnitStatus.ACTIVE,
                housekeeping_status=HousekeepingStatus.CLEAN,
                floor=str((idx + 1) // 2),
            )
        )
    db.add_all(units)
    db.flush()

    guests = [
        Guest(
            organization_id=organization_id,
            full_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            email=f"guest{i}@example.com",
            phone=f"+3598{random.randint(10000000, 99999999)}",
        )
        for i in range(1, 16)
    ]
    db.add_all(guests)
    db.flush()

    # Reservations spread over last month → next month, avoiding overlaps per unit.
    reservations: list[Reservation] = []
    for unit in units:
        cursor = today - timedelta(days=45)
        while cursor < today + timedelta(days=45):
            gap = random.randint(0, 6)
            nights = random.randint(1, 6)
            check_in = cursor + timedelta(days=gap)
            check_out = check_in + timedelta(days=nights)
            cursor = check_out

            source = random.choices(
                [s for s, _ in SOURCE_WEIGHTS], weights=[w for _, w in SOURCE_WEIGHTS]
            )[0]
            nightly = unit.base_price or Decimal("80")
            gross = (nightly * nights).quantize(Decimal("0.01"))
            fees = (gross * FEE_RATE[source]).quantize(Decimal("0.01"))

            if check_out < today:
                status = ReservationStatus.CHECKED_OUT
                payment_status = PaymentStatus.PAID
            elif check_in <= today < check_out:
                status = ReservationStatus.IN_HOUSE
                payment_status = PaymentStatus.PAID
            else:
                status = ReservationStatus.CONFIRMED
                payment_status = PaymentStatus.PENDING

            guest = random.choice(guests)
            reservations.append(
                Reservation(
                    property_id=unit.property_id,
                    unit_id=unit.id,
                    guest_id=guest.id,
                    guest_name=guest.full_name,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    number_of_guests=min(unit.capacity, random.randint(1, 4)),
                    source=source,
                    source_reference=(
                        f"HM{random.randint(100000, 999999)}"
                        if source in (ReservationSource.AIRBNB, ReservationSource.BOOKING)
                        else "Called on mobile"
                    ),
                    status=status,
                    gross_amount=gross,
                    fees_amount=fees,
                    net_payout_amount=gross - fees,
                    currency="EUR",
                    payment_method=PAYMENT_BY_SOURCE[source],
                    payment_status=payment_status,
                    payout_date=check_out + timedelta(days=2)
                    if payment_status is PaymentStatus.PAID
                    else None,
                )
            )
    db.add_all(reservations)
    db.flush()

    # A couple of maintenance tasks so the board is not only housekeeping.
    db.add_all(
        [
            Task(
                property_id=seaside.id,
                unit_id=units[2].id,
                task_type=TaskType.MAINTENANCE_ISSUE,
                status=TaskStatus.SCHEDULED,
                priority=TaskPriority.HIGH,
                assigned_to="Georgi",
                estimated_duration_minutes=90,
                due_date=today,
                description="AC not cooling — check gas pressure.",
                changes_room_status_to=HousekeepingStatus.CLEAN,
            ),
            Task(
                property_id=central.id,
                unit_id=None,
                task_type=TaskType.INSPECTION,
                status=TaskStatus.SCHEDULED,
                priority=TaskPriority.NORMAL,
                assigned_to="Owner",
                estimated_duration_minutes=30,
                due_date=today,
                description="Monthly walk-through of common areas and stairwell.",
            ),
        ]
    )
    db.flush()

    logger.info(
        "Seeded %s properties, %s units, %s reservations.",
        2,
        len(units),
        len(reservations),
    )


def main() -> None:
    configure_logging()
    require_schema()
    with SessionLocal() as db:
        owner = ensure_owner(db)
        seed(db, owner.organization_id)
        db.commit()


if __name__ == "__main__":
    main()
