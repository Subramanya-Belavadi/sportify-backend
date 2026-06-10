from fastapi import APIRouter, HTTPException, Query
from app.database import get_pool
from app.models import Venue, Slot

router = APIRouter(prefix="/venues", tags=["venues"])


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
    date: str = Query(..., description="Format: YYYY-MM-DD"),
):
    pool = get_pool()

    venue = await pool.fetchrow("SELECT id FROM venues WHERE id = $1", venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    rows = await pool.fetch("""
        SELECT id, venue_id, date::TEXT, start_time::TEXT, end_time::TEXT, status, booked_by
        FROM slots
        WHERE venue_id = $1 AND date = $2::DATE
        ORDER BY start_time
    """, venue_id, date)

    return [dict(r) for r in rows]
