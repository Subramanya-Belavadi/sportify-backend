import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

pool: asyncpg.Pool | None = None


async def connect_db():
    global pool
    pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"), min_size=2, max_size=10)


async def disconnect_db():
    global pool
    if pool:
        await pool.close()


def get_pool() -> asyncpg.Pool:
    return pool
