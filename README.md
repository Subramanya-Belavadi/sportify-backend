# Sportify Backend

FastAPI + PostgreSQL backend for the Sportify sports slot booking app.

## Setup

### 1. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.sample .env
# Paste your PostgreSQL connection string into DATABASE_URL
```

### 3. Create tables and seed data
```bash
python -m app.seed
```

### 4. Run locally
```bash
uvicorn app.main:app --reload --port 3000
```

API docs available at: http://localhost:3000/docs

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /venues | List all venues |
| GET | /venues/{id}/slots?date=YYYY-MM-DD | Slots for a venue on a date |
| POST | /bookings | Book a slot (concurrency-safe) |
| GET | /users/{id}/bookings | User's bookings |
| DELETE | /bookings/{id} | Cancel a booking |

All write endpoints require `X-User-Id` header.

---

## Concurrency & Double-booking

The booking endpoint uses a single atomic SQL UPDATE:

```sql
UPDATE slots
SET status = 'booked', booked_by = $user_id
WHERE id = $slot_id AND status = 'available'
RETURNING *;
```

If two requests arrive simultaneously, PostgreSQL's row-level locking ensures only one UPDATE succeeds. The other gets 0 rows back → 409 Conflict returned to the client.

Additionally, the `bookings` table has a `UNIQUE (slot_id)` constraint — so even a direct database INSERT cannot create a duplicate booking, bypassing the API entirely.

---

## Deploy on Railway

1. Create new project on Railway
2. Add PostgreSQL plugin — `DATABASE_URL` is injected automatically
3. Connect this repo, set root directory to `/` (or wherever server lives)
4. Railway detects `Procfile` and runs: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Run seed: use Railway shell or run locally against the Railway DB URL

---

## Demo users

| User ID | Name |
|---------|------|
| user_1 | Alice |
| user_2 | Bob |
| user_3 | Charlie |
