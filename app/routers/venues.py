from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query, Header
from app.database import get_pool
from app.models import Venue, Slot

router = APIRouter(prefix="/venues", tags=["venues"])

RESERVE_MINUTES = 2


@router.get("", response_model=list[Venue])
async def list_venues():
    pool = get_pool()
    rows = await pool.fetch("""
        SELECT id, name, address, sport, image_url, price_per_hour
        FROM venues
        ORDER BY name
    """)
    return [dict(r) for r in rows]


@router.get("/{venue_id}/slots", response_model=list[Slot])
async def get_slots(
    venue_id: str,
    date_str: str = Query(..., alias="date", description="Format: YYYY-MM-DD"),
):
    pool = get_pool()

    venue = await pool.fetchrow("SELECT id FROM venues WHERE id = $1", venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    async with pool.acquire() as conn:
        # Expire stale reservations before returning slots
        await conn.execute("""
            UPDATE slots SET status = 'available', reserved_by = NULL, reserved_until = NULL
            WHERE status = 'reserved' AND reserved_until < NOW()
        """)

        rows = await conn.fetch("""
            SELECT id, venue_id, date::TEXT, start_time::TEXT, end_time::TEXT, status, booked_by
            FROM slots
            WHERE venue_id = $1 AND date = $2
            ORDER BY start_time
        """, venue_id, date.fromisoformat(date_str))

    return [dict(r) for r in rows]


@router.post("/{venue_id}/slots/{slot_id}/reserve")
async def reserve_slot(
    venue_id: str,
    slot_id: str,
    x_user_id: str = Header(...),
):
    pool = get_pool()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESERVE_MINUTES)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Expire stale reservations first
            await conn.execute("""
                UPDATE slots SET status = 'available', reserved_by = NULL, reserved_until = NULL
                WHERE status = 'reserved' AND reserved_until < NOW()
            """)

            # Try to reserve: succeeds if available, or already reserved by same user
            result = await conn.fetchrow("""
                UPDATE slots
                SET status = 'reserved', reserved_by = $1, reserved_until = $2
                WHERE id = $3
                  AND venue_id = $4
                  AND (
                    status = 'available'
                    OR (status = 'reserved' AND reserved_by = $1)
                  )
                RETURNING id, reserved_until::TEXT
            """, x_user_id, expires_at, slot_id, venue_id)

            if not result:
                raise HTTPException(status_code=409, detail="Slot is no longer available")

    return {"slot_id": result["id"], "expires_at": result["reserved_until"]}
