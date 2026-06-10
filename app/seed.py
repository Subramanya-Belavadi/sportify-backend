"""
Run once to create tables and seed data:
  python -m app.seed
"""
import asyncio
import asyncpg
import os
import uuid
from datetime import date, time, timedelta
from dotenv import load_dotenv

load_dotenv()

VENUES = [
    {"id": "v1", "name": "Smash Arena", "address": "Koramangala, Bangalore", "sport": "Badminton", "image_url": "assets/images/badminton-court.jpg", "price_per_hour": 400},
    {"id": "v2", "name": "Green Turf", "address": "Whitefield, Bangalore", "sport": "Football", "image_url": "assets/images/football-court.jpg", "price_per_hour": 800},
    {"id": "v3", "name": "Box Cricket Hub", "address": "Electronic City, Bangalore", "sport": "Box Cricket", "image_url": "assets/images/cricket-court.jpg", "price_per_hour": 1200},
    {"id": "v4", "name": "Pickle House", "address": "Marathahalli, Bangalore", "sport": "Pickleball", "image_url": "assets/images/pickleball-court.jpg", "price_per_hour": 500},
]

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS venues (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    address     TEXT NOT NULL,
    sport       TEXT NOT NULL,
    image_url   TEXT DEFAULT '',
    price_per_hour NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS slots (
    id          TEXT PRIMARY KEY,
    venue_id    TEXT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    status      TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'booked')),
    booked_by   TEXT,
    CONSTRAINT unique_venue_slot UNIQUE (venue_id, date, start_time)
);

CREATE TABLE IF NOT EXISTS bookings (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id     TEXT NOT NULL,
    slot_id     TEXT NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    venue_id    TEXT NOT NULL,
    venue_name  TEXT NOT NULL,
    date        DATE NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    status      TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_active_booking UNIQUE (slot_id)
);
"""

# Slots: 6 AM to 10 PM, 1 hour each = 16 slots per venue per day
SLOT_HOURS = range(6, 22)


async def seed():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL"))

    print("Creating tables...")
    await conn.execute(CREATE_TABLES)

    print("Seeding venues...")
    for v in VENUES:
        await conn.execute("""
            INSERT INTO venues (id, name, address, sport, image_url, price_per_hour)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO NOTHING
        """, v["id"], v["name"], v["address"], v["sport"], v["image_url"], v["price_per_hour"])

    print("Seeding slots for next 14 days...")
    today = date.today()
    records = []
    for day_offset in range(14):
        slot_date = today + timedelta(days=day_offset)
        for venue in VENUES:
            for hour in SLOT_HOURS:
                records.append((
                    f"{venue['id']}_{slot_date}_{hour:02d}",
                    venue["id"],
                    slot_date,
                    time(hour, 0),
                    time(hour + 1, 0),
                ))

    await conn.executemany("""
        INSERT INTO slots (id, venue_id, date, start_time, end_time, status)
        VALUES ($1, $2, $3, $4, $5, 'available')
        ON CONFLICT DO NOTHING
    """, records)

    await conn.close()
    print("Done. Database seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
