# BookingMngr

Internal management app for one owner/manager running several hotels and
apartment buildings. Unifies reservations from Airbnb, Booking.com, phone,
WhatsApp and email into one model, drives daily housekeeping and maintenance,
and reports what actually landed in the owner's pocket.

Single user, single tenant — but the tenant boundary is modelled explicitly so
multi-tenant is a later configuration change, not a rewrite.

```
backend/    FastAPI + SQLAlchemy 2.0 + PostgreSQL
frontend/   Next.js (App Router) + TypeScript + Tailwind v4
```

## Quick start

**1. Database**

```bash
docker compose up -d db          # Postgres 16 on :5432
```

**2. Backend**

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env             # set SECRET_KEY and OWNER_PASSWORD
.venv/bin/python -m alembic upgrade head   # schema
.venv/bin/python -m app.db.init_db         # owner account
.venv/bin/python -m app.db.seed            # optional demo data
.venv/bin/python -m uvicorn app.main:app --reload
```

Alembic owns the schema; `init_db` only creates the organization and owner
account, and refuses to run against an unmigrated database.

API on http://localhost:8000, interactive docs at `/docs`.

**3. Frontend**

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

UI on http://localhost:3000. Sign in with `OWNER_USERNAME` / `OWNER_PASSWORD`.

**Tests**

```bash
cd backend && .venv/bin/python -m pytest tests -q     # SQLite, no services needed
cd frontend && npm run typecheck && npm run build
```

The suite also runs against the real target — worth doing before a release,
since SQLite is lenient about things Postgres is not:

```bash
docker exec bookingmngr-db psql -U bookingmngr -c "CREATE DATABASE bookingmngr_test"
cd backend && TEST_DATABASE_URL=postgresql+psycopg://bookingmngr:bookingmngr@localhost:5432/bookingmngr_test \
    .venv/bin/python -m pytest tests -q
```

Stop `next dev` before running `npm run build` — they share `.next`, and a
concurrent build leaves the dev server serving broken chunks.

## Domain model

| Entity | Purpose |
| --- | --- |
| `Organization` | Tenant boundary. One row today. |
| `User` | The owner account. `role` is a placeholder for later staff logins. |
| `Property` | Hotel / apartment building / mixed. Archived, never deleted, once it has history. |
| `Unit` | Room or apartment. Carries `housekeeping_status` and `cleaning_duration_minutes`. |
| `Guest` | Optional. Reservations also keep a denormalised `guest_name` so a phone booking needs no guest record. |
| `Reservation` | The unified booking. Channel, dates, status, and the money (`gross` / `fees` / `net_payout`). |
| `Task` | Housekeeping and maintenance. `changes_room_status_to` links completion to unit state. |
| `Payout` | Empty in the MVP — see below. |
| `AuditLog` | Append-only record of status changes and completions. |

### Design decisions worth knowing

**Money lives on the reservation, for now.** `net_payout_amount` is the single
figure every report sums; `gross_amount − fees_amount` is the default when it
isn't supplied. The `Payout` table already exists and is wired to
`Reservation.payouts`, so splitting one booking across several payouts later
means backfilling rows and pointing `services/reports.py` at them — no schema
churn in `Reservation`.

**Revenue is attributed to the check-out month.** That's when the stay is
finished and the OTA statement lands, which is how the owner reconciles. It is
one function (`services/reports.monthly_revenue`) if you'd rather accrue
nightly.

**Enums are VARCHAR, not PG enums.** Adding `source = "expedia"` is a code
change, not a migration. See `models/types.enum_column`.

**Double bookings are rejected twice over.** Creating, moving or reopening a
reservation checks the unit for an overlapping stay in a blocking status. That
check reads before it writes, so Postgres backstops it with an exclusion
constraint (`ex_reservations_no_overlap`) that no concurrent request or manual
`INSERT` can slip past; the loser of a race gets the same 409. Check-out day is
free for the next guest, so back-to-back bookings work, and canceled bookings
release their dates. The constraint needs `btree_gist` and is Postgres-only —
on SQLite the service check stands alone.

**Housekeeping generation is idempotent.** `POST /tasks/generate-housekeeping`
skips reservations that already have a task for that day, so the manager can hit
the button twice without making a mess. It also flips departing units to
`dirty`, and completing the clean flips them back via `changes_room_status_to`.

## API

Versioned under `/api/v1`. Everything except `POST /auth/login` needs a bearer
token.

```
POST   /auth/login                     GET    /auth/me

GET    /properties                     POST   /properties
GET    /properties/{id}                PATCH  /properties/{id}
DELETE /properties/{id}                # archives; ?hard_delete=true if no history

GET    /properties/{id}/units          POST   /properties/{id}/units
GET    /units/{id}                     PATCH  /units/{id}      # incl. housekeeping_status
DELETE /units/{id}                     # archives

GET    /guests                         POST   /guests
GET    /guests/{id}                    PATCH  /guests/{id}

GET    /reservations                   # property_id, unit_id, from_date, to_date, status, source, search
POST   /reservations
GET    /reservations/daily             # ?date=&property_id=  → arrivals / departures / in_house
GET    /reservations/calendar          # ?property_id=&year=&month=
GET    /reservations/{id}              PATCH  /reservations/{id}
DELETE /reservations/{id}              # prefer status=canceled / no_show

GET    /tasks                          # date, from_date, to_date, property_id, unit_id, status, task_type
POST   /tasks                          POST   /tasks/generate-housekeeping
GET    /tasks/{id}                     PATCH  /tasks/{id}      DELETE /tasks/{id}

GET    /reports/daily-board            # ?date=&property_id=
GET    /reports/monthly-revenue        # ?year=&month=&property_id=
```

## Frontend screens

| Route | What it does |
| --- | --- |
| `/dashboard` | Morning board: arrivals, departures, in-house and today's tasks per property, plus occupancy / tasks-done / revenue-MTD KPIs. |
| `/calendar` | Month grid, rows = units, blocks coloured by channel. Click a block for the side panel. |
| `/reservations` | Filterable table, "Add reservation" form for phone/WhatsApp/email bookings. |
| `/reservations/[id]` | Edit dates, status, payout figures, notes. |
| `/tasks` | Day board grouped by status or unit; complete/assign/edit inline; generate checkout cleans. |
| `/reports` | Monthly revenue by channel with the contributing reservations. |
| `/properties`, `/properties/[id]`, `/units/[id]` | Property and unit management. |

The top bar carries the shared working date and property selector
(`lib/app-context.tsx`); pages read from it rather than each keeping their own.

## Adding channel integrations later

`services/ota/` is the seam. `base.py` defines `ChannelAdapter` and the
`NormalizedReservation` payload; `airbnb.py` and `booking.py` are stubs that
raise `NotImplementedError`. Routers never touch channel code, so a real
importer (iCal first — both platforms expose per-listing feeds — then email
parsing, then partner APIs) plugs in without touching endpoints or models.
`Reservation.external_payload` is there to keep the raw feed data for
reconciliation.

## Known gaps

- Frontend types in `lib/types.ts` are hand-maintained. Generating them from
  `/api/v1/openapi.json` is the obvious next step.
- Auth is a long-lived bearer token in `localStorage` — fine for a single
  internal user, worth revisiting if staff accounts are added.
- Test coverage is API-level only; there are no frontend tests.
- The overlap constraint's status list is frozen in its migration. Adding a
  status that should hold a unit means writing a migration to rebuild it, not
  just editing `BLOCKING_RESERVATION_STATUSES`.
