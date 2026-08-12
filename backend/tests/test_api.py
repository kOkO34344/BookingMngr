"""Smoke coverage for the core flows: CRUD, calendar, housekeeping, reports."""

from datetime import date, timedelta

TODAY = date.today()


def _create_property(client, api, name="Seaside Hotel"):
    response = client.post(
        f"{api}/properties",
        json={"name": name, "type": "hotel", "city": "Varna", "country": "Bulgaria"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_unit(client, api, property_id, name="101"):
    response = client.post(
        f"{api}/properties/{property_id}/units",
        json={"name_or_number": name, "capacity": 2, "base_price": "80.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_reservation(client, api, property_id, unit_id, check_in, check_out, **extra):
    payload = {
        "property_id": property_id,
        "unit_id": unit_id,
        "guest_name": "Maria Petrova",
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "number_of_guests": 2,
        "source": "airbnb",
        "source_reference": "HMABC123",
        "status": "confirmed",
        "gross_amount": "300.00",
        "fees_amount": "45.00",
        "payment_method": "airbnb_payout",
        "payment_status": "paid",
        **extra,
    }
    return client.post(f"{api}/reservations", json=payload)


def test_login_required(client, api):
    unauthenticated = client.get(f"{api}/properties", headers={"Authorization": ""})
    assert unauthenticated.status_code == 401


def test_property_and_unit_crud(client, api):
    prop = _create_property(client, api)
    assert prop["units_count"] == 0

    unit = _create_unit(client, api, prop["id"])
    assert unit["housekeeping_status"] == "clean"

    listing = client.get(f"{api}/properties").json()
    assert listing[0]["units_count"] == 1

    patched = client.patch(
        f"{api}/units/{unit['id']}", json={"housekeeping_status": "dirty"}
    ).json()
    assert patched["housekeeping_status"] == "dirty"

    duplicate = client.post(
        f"{api}/properties/{prop['id']}/units", json={"name_or_number": "101"}
    )
    assert duplicate.status_code == 409

    archived = client.delete(f"{api}/properties/{prop['id']}")
    assert archived.status_code == 200
    assert client.get(f"{api}/properties").json() == []


def test_reservation_net_payout_defaults_and_overlap_is_rejected(client, api):
    prop = _create_property(client, api)
    unit = _create_unit(client, api, prop["id"])

    created = _create_reservation(
        client, api, prop["id"], unit["id"], TODAY, TODAY + timedelta(days=3)
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["net_payout_amount"] == "255.00"  # gross - fees
    assert body["nights"] == 3
    assert body["unit_name"] == "101"

    clash = _create_reservation(
        client,
        api,
        prop["id"],
        unit["id"],
        TODAY + timedelta(days=1),
        TODAY + timedelta(days=2),
    )
    assert clash.status_code == 409

    # Back-to-back stays are fine: checkout day frees the unit.
    back_to_back = _create_reservation(
        client,
        api,
        prop["id"],
        unit["id"],
        TODAY + timedelta(days=3),
        TODAY + timedelta(days=5),
    )
    assert back_to_back.status_code == 201


def test_canceling_frees_the_unit_and_reopening_is_rejected(client, api):
    """A canceled booking releases its dates — but cannot silently reclaim them."""
    prop = _create_property(client, api)
    unit = _create_unit(client, api, prop["id"])

    first = _create_reservation(
        client, api, prop["id"], unit["id"], TODAY, TODAY + timedelta(days=3)
    ).json()

    canceled = client.patch(
        f"{api}/reservations/{first['id']}", json={"status": "canceled"}
    )
    assert canceled.status_code == 200

    # The dates are free again, so the same slot can be sold to someone else.
    replacement = _create_reservation(
        client, api, prop["id"], unit["id"], TODAY, TODAY + timedelta(days=3)
    )
    assert replacement.status_code == 201, replacement.text

    # Reopening the canceled one would now double-book the unit.
    reopened = client.patch(
        f"{api}/reservations/{first['id']}", json={"status": "confirmed"}
    )
    assert reopened.status_code == 409, reopened.text


def test_daily_and_calendar_views(client, api):
    prop = _create_property(client, api)
    unit = _create_unit(client, api, prop["id"])
    _create_reservation(
        client, api, prop["id"], unit["id"], TODAY - timedelta(days=2), TODAY
    )

    daily = client.get(f"{api}/reservations/daily", params={"date": TODAY.isoformat()}).json()
    assert len(daily["departures"]) == 1
    assert daily["arrivals"] == []

    calendar = client.get(
        f"{api}/reservations/calendar",
        params={"property_id": prop["id"], "year": TODAY.year, "month": TODAY.month},
    ).json()
    assert calendar["units"][0]["unit_id"] == unit["id"]
    assert len(calendar["units"][0]["blocks"]) == 1


def test_generate_housekeeping_is_idempotent_and_marks_units_dirty(client, api):
    prop = _create_property(client, api)
    unit = _create_unit(client, api, prop["id"])
    _create_reservation(
        client, api, prop["id"], unit["id"], TODAY - timedelta(days=2), TODAY
    )

    first = client.post(
        f"{api}/tasks/generate-housekeeping",
        json={"date": TODAY.isoformat(), "property_id": prop["id"]},
    )
    assert first.status_code == 201, first.text
    generated = first.json()
    assert len(generated["created"]) == 1
    assert generated["units_marked_dirty"] == [unit["id"]]
    assert client.get(f"{api}/units/{unit['id']}").json()["housekeeping_status"] == "dirty"

    second = client.post(
        f"{api}/tasks/generate-housekeeping",
        json={"date": TODAY.isoformat(), "property_id": prop["id"]},
    ).json()
    assert second["created"] == []
    assert second["skipped_existing"] == 1

    # Completing the clean flips the unit back to clean.
    task_id = generated["created"][0]["id"]
    completed = client.patch(f"{api}/tasks/{task_id}", json={"status": "completed"}).json()
    assert completed["completed_at"] is not None
    assert client.get(f"{api}/units/{unit['id']}").json()["housekeeping_status"] == "clean"


def test_daily_board_and_monthly_revenue(client, api):
    prop = _create_property(client, api)
    unit_a = _create_unit(client, api, prop["id"], "101")
    unit_b = _create_unit(client, api, prop["id"], "102")

    # In-house tonight.
    _create_reservation(
        client,
        api,
        prop["id"],
        unit_a["id"],
        TODAY - timedelta(days=1),
        TODAY + timedelta(days=2),
        status="in_house",
    )
    # Checked out earlier this month, cash booking.
    _create_reservation(
        client,
        api,
        prop["id"],
        unit_b["id"],
        TODAY.replace(day=1),
        TODAY.replace(day=1) + timedelta(days=2),
        status="checked_out",
        source="phone",
        gross_amount="200.00",
        fees_amount="0.00",
        payment_method="cash",
    )

    board = client.get(f"{api}/reports/daily-board", params={"date": TODAY.isoformat()}).json()
    assert board["totals"]["total_units"] == 2
    assert board["totals"]["in_house_count"] == 1
    assert board["totals"]["occupancy_pct"] == 50.0

    revenue = client.get(
        f"{api}/reports/monthly-revenue",
        params={"year": TODAY.year, "month": TODAY.month},
    ).json()
    sources = {entry["source"]: entry for entry in revenue["by_source"]}
    assert "phone" in sources
    assert sources["phone"]["net_payout_amount"] == "200.00"
    assert revenue["properties"][0]["property_name"] == "Seaside Hotel"
