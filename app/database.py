import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

pool: asyncpg.Pool | None = None


async def connect_db():
    global pool
    dsn = os.getenv("DATABASE_URL")
    ssl = "require" if os.getenv("RAILWAY_ENVIRONMENT") else None
    pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10, ssl=ssl)


async def disconnect_db():
    global pool
    if pool:
        await pool.close()


def get_pool() -> asyncpg.Pool:
    return pool
