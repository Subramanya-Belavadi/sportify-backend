from fastapi import APIRouter, HTTPException
from app.database import get_pool
from app.models import Booking

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/bookings", response_model=list[Booking])
async def get_user_bookings(user_id: str):
    pool = get_pool()
    rows = await pool.fetch("""
        SELECT id, user_id, first_slot_id AS slot_id, venue_id, venue_name,
               date::TEXT, start_time::TEXT, end_time::TEXT,
               duration_hours, base_amount, gst_amount, total_amount,
               status, created_at::TEXT
        FROM bookings
        WHERE user_id = $1
        ORDER BY created_at DESC
    """, user_id)
    return [dict(r) for r in rows]
