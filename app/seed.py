"""
Run once to seed the database:
  python -m app.seed
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

VENUES = [
    {"id": "v1", "name": "Smash Arena", "address": "Koramangala, Bangalore", "sport": "Badminton", "image_url": "", "price_per_hour": 400},
    {"id": "v2", "name": "Green Turf", "address": "Whitefield, Bangalore", "sport": "Football", "image_url": "", "price_per_hour": 800},
    {"id": "v3", "name": "Court Kings", "address": "Indiranagar, Bangalore", "sport": "Badminton", "image_url": "", "price_per_hour": 350},
    {"id": "v4", "name": "Goal Zone", "address": "HSR Layout, Bangalore", "sport": "Football", "image_url": "", "price_per_hour": 700},
    {"id": "v5", "name": "Rally Club", "address": "JP Nagar, Bangalore", "sport": "Badminton", "image_url": "", "price_per_hour": 300},
]

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS venues (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    sport TEXT NOT NULL,
    image_url TEXT DEFAULT '',
    price_per_hour NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS slots (
    id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL REFERENCES venues(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    booked_by TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id TEXT NOT NULL,
    slot_id TEXT NOT NULL REFERENCES slots(id),
    venue_id TEXT NOT NULL,
    venue_name TEXT NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def seed():
    conn = await asyncpg.connect(dsn=os.getenv("DATABASE_URL"))
    await conn.execute(CREATE_TABLES)

    for v in VENUES:
        await conn.execute("""
            INSERT INTO venues (id, name, address, sport, image_url, price_per_hour)
            VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING
        """, v["id"], v["name"], v["address"], v["sport"], v["image_url"], v["price_per_hour"])

    # TODO: seed slots for each venue — 6AM to 10PM hourly for next 7 days

    await conn.close()
    print("Seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
