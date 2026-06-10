# Sportify Backend

FastAPI + PostgreSQL backend for the Sportify sports venue booking app. Handles authentication, venue/slot management, real-time slot reservation with a 2-minute hold, and concurrency-safe booking.

---

## Tech Stack

| Concern | Library |
|---------|---------|
| API framework | FastAPI 0.115 |
| Async DB driver | asyncpg 0.30 |
| Password hashing | passlib (bcrypt) |
| Data validation | Pydantic v2 |
| Server | Uvicorn (ASGI) |
| Env config | python-dotenv |

---

## Project Structure

```
sportify_backend/
├── app/
│   ├── main.py          # FastAPI app, lifespan, router registration
│   ├── database.py      # asyncpg connection pool (min 2, max 10)
│   ├── models.py        # Pydantic request/response models + GST_RATE
│   ├── seed.py          # Table creation, migrations, venue + slot seeding
│   └── routers/
│       ├── auth.py      # POST /auth/signup, /auth/login
│       ├── venues.py    # GET /venues, GET slots, POST reserve
│       ├── bookings.py  # POST /bookings, DELETE /bookings/:id
│       └── users.py     # GET /users/:id/bookings
├── Procfile             # web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
└── requirements.txt
```

---

## Database Schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `gen_random_uuid()` |
| name | TEXT | |
| email | TEXT UNIQUE | Stored lowercase |
| password_hash | TEXT | bcrypt |
| created_at | TIMESTAMPTZ | Default NOW() |

### `venues`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | e.g. `v1` |
| name | TEXT | |
| address | TEXT | |
| sport | TEXT | |
| image_url | TEXT | Asset path or network URL |
| price_per_hour | NUMERIC | |

### `slots`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | Format: `{venue_id}_{date}_{HH}` e.g. `v1_2026-06-11_09` |
| venue_id | TEXT FK | → venues |
| date | DATE | |
| start_time | TIME | |
| end_time | TIME | |
| status | TEXT | `available` / `booked` / `reserved` |
| booked_by | TEXT | User ID if booked |
| reserved_by | TEXT | User ID holding the 2-min reservation |
| reserved_until | TIMESTAMPTZ | Reservation expiry |

Constraint: `UNIQUE (venue_id, date, start_time)`

### `bookings`
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | `gen_random_uuid()` |
| user_id | TEXT | |
| first_slot_id | TEXT | Anchor slot (multi-hour bookings span consecutive slots) |
| venue_id | TEXT | |
| venue_name | TEXT | Cached at booking time |
| date | DATE | |
| start_time | TIME | |
| end_time | TIME | Computed from duration |
| duration_hours | INT | 1–4 |
| base_amount | NUMERIC | `price_per_hour × duration` |
| gst_amount | NUMERIC | 18% of base |
| total_amount | NUMERIC | base + gst |
| status | TEXT | `confirmed` / `cancelled` |
| created_at | TIMESTAMPTZ | |

---

## API Reference

All write endpoints require the **`X-User-Id`** header.

### Auth — `/auth`

#### `POST /auth/signup`
Register a new user.

**Request body:**
```json
{ "name": "Alice", "email": "alice@example.com", "password": "Secret@123" }
```

**Validation:**
- All fields required
- Valid email format
- Password: 8+ characters, at least one letter, one digit, one symbol

**Response `201`:**
```json
{ "user_id": "uuid", "name": "Alice", "email": "alice@example.com" }
```

**Errors:** `409` email already registered · `422` validation failed

---

#### `POST /auth/login`
Authenticate an existing user.

**Request body:**
```json
{ "email": "alice@example.com", "password": "Secret@123" }
```

**Response `200`:**
```json
{ "user_id": "uuid", "name": "Alice", "email": "alice@example.com" }
```

**Errors:** `401` invalid credentials

---

### Venues — `/venues`

#### `GET /venues`
Returns all venues ordered by name.

**Response `200`:**
```json
[
  {
    "id": "v1",
    "name": "Smash Arena",
    "address": "Koramangala, Bangalore",
    "sport": "Badminton",
    "image_url": "assets/images/badminton-court.jpg",
    "price_per_hour": 400.0
  }
]
```

---

#### `GET /venues/{venue_id}/slots?date=YYYY-MM-DD`
Returns all slots for a venue on a given date. Expired reservations are automatically cleared before the response is built.

**Response `200`:**
```json
[
  {
    "id": "v1_2026-06-11_09",
    "venue_id": "v1",
    "date": "2026-06-11",
    "start_time": "09:00:00",
    "end_time": "10:00:00",
    "status": "available",
    "booked_by": null
  }
]
```

**Errors:** `404` venue not found

---

#### `POST /venues/{venue_id}/slots/{slot_id}/reserve`
Places a 2-minute server-side hold on a slot. Re-calling with the same user extends the hold. Another user holding the slot returns `409`.

**Headers:** `X-User-Id: <uuid>`

**Response `200`:**
```json
{ "slot_id": "v1_2026-06-11_09", "expires_at": "2026-06-11T09:02:00Z" }
```

**Errors:** `409` slot already reserved or booked

---

### Bookings — `/bookings`

#### `POST /bookings`
Confirms a booking. Accepts slots that are `available` **or** `reserved` by the same user. Books all consecutive slots atomically.

**Headers:** `X-User-Id: <uuid>`

**Request body:**
```json
{ "slot_id": "v1_2026-06-11_09", "user_id": "uuid", "duration_hours": 2 }
```

**Response `201`:**
```json
{
  "id": "booking-uuid",
  "user_id": "uuid",
  "slot_id": "v1_2026-06-11_09",
  "venue_id": "v1",
  "venue_name": "Smash Arena",
  "date": "2026-06-11",
  "start_time": "09:00:00",
  "end_time": "11:00:00",
  "duration_hours": 2,
  "base_amount": 800.0,
  "gst_amount": 144.0,
  "total_amount": 944.0,
  "status": "confirmed",
  "created_at": "2026-06-11T03:45:00Z"
}
```

**Errors:** `409` slot taken or user time-overlap conflict · `422` invalid duration

---

#### `GET /users/{user_id}/bookings`
Returns all bookings (confirmed and cancelled) for a user, newest first.

**Response `200`:** Array of booking objects (same shape as above)

---

#### `DELETE /bookings/{booking_id}`
Cancels a booking and frees all associated slots back to `available`.

**Headers:** `X-User-Id: <uuid>`

**Response `204`** (no body)

**Errors:** `403` not your booking · `404` not found · `409` already cancelled

---

## Concurrency & Double-Booking Prevention

Three independent layers guard against double-bookings:

### Layer 1 — Atomic SQL UPDATE
The booking endpoint updates all required slots in a single statement inside a transaction. PostgreSQL's row-level locking ensures only one concurrent request wins:

```sql
UPDATE slots
SET status = 'booked', booked_by = $user_id,
    reserved_by = NULL, reserved_until = NULL
WHERE id = ANY($slot_ids::text[])
  AND (status = 'available'
       OR (status = 'reserved' AND reserved_by = $user_id))
RETURNING id;
```

If `rowcount != duration_hours`, the transaction rolls back automatically and a `409` is returned.

### Layer 2 — User Overlap Check
Before booking, a query checks for confirmed bookings by the same user that overlap the requested window on the same date:

```sql
SELECT COUNT(*) FROM bookings
WHERE user_id = $user_id AND date = $date AND status = 'confirmed'
  AND start_time < $requested_end AND end_time > $requested_start
```

Returns `409` if any overlap exists, preventing a user from double-booking their own time.

### Layer 3 — Soft Reservation (2-Minute Hold)
`POST /venues/{id}/slots/{slot_id}/reserve` sets `status = 'reserved'` for 2 minutes. The slot is invisible to other users during the hold. The booking endpoint honours reservations made by the same user, so the confirmation flow is: reserve → countdown → confirm.

Expired reservations are cleaned up automatically whenever slots are fetched.

---

## Seeded Venues

| ID | Name | Sport | Location | Price/hr |
|----|------|-------|----------|----------|
| v1 | Smash Arena | Badminton | Koramangala | ₹400 |
| v2 | Green Turf | Football | Whitefield | ₹800 |
| v3 | Box Cricket Hub | Box Cricket | Electronic City | ₹1200 |
| v4 | Pickle House | Pickleball | Marathahalli | ₹500 |
| v5 | Rally Court | Badminton | Indiranagar | ₹450 |
| v6 | Dink Zone | Pickleball | HSR Layout | ₹550 |

16 hourly slots per venue per day (6 AM – 10 PM), seeded for the next 14 days.

---

## Local Setup

### 1. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.sample .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/sportify
```

### 3. Seed the database
```bash
python -m app.seed
```

This creates all tables, applies migrations (adds `reserved_by` / `reserved_until` columns and updates the status check constraint), seeds all venues, and generates 14 days of slots.

> Re-running seed is safe — venues and slots use `ON CONFLICT DO NOTHING`. The `bookings` table is dropped and recreated on each run (dev convenience).

### 4. Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Deploy on Railway

### Step 1 — Create the project

1. Go to [railway.app](https://railway.app) and click **New Project**
2. Choose **Deploy from GitHub repo** and select this repository
3. Set the **Root Directory** to the backend folder if it's in a monorepo (e.g. `sportify_backend`)

### Step 2 — Add PostgreSQL

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway injects `DATABASE_URL` automatically into your service — no manual config needed

### Step 3 — Set environment variables

In your service's **Variables** tab, confirm `DATABASE_URL` is present (injected by Railway). No other variables are required.

### Step 4 — Deploy

Railway detects the `Procfile` and runs:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The first deploy will go live automatically. Watch the **Deploy Logs** tab for startup confirmation.

### Step 5 — Seed the database

After the first deploy, open the Railway service's **Shell** tab and run:
```bash
python -m app.seed
```

This creates all tables and seeds venues + slots against the production database.

### Step 6 — Update the Flutter app

Copy your Railway public domain (e.g. `https://sportify-backend-production.up.railway.app`) and update the Flutter `.env`:

```env
API_BASE_URL=https://sportify-backend-production.up.railway.app
```

### Re-seeding slots (scheduled task)

Slots are seeded for 14 days ahead. To keep slots rolling, re-run `python -m app.seed` periodically from the Railway shell. Existing available slots are preserved (`ON CONFLICT DO NOTHING`).
