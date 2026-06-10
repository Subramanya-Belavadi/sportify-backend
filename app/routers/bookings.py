from datetime import date, time
from fastapi import APIRouter, HTTPException, Header
from app.database import get_pool
from app.models import BookingRequest, Booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def _validate_user(x_user_id: str, pool) -> None:
    user = await pool.fetchrow("SELECT id FROM users WHERE id = $1", x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")


@router.post("", response_model=Booking, status_code=201)
async def book_slot(
    body: BookingRequest,
    x_user_id: str = Header(..., description="User ID from login"),
):
    pool = get_pool()
    await _validate_user(x_user_id, pool)

    async with pool.acquire() as conn:
        async with conn.transaction():
            updated = await conn.fetchrow("""
                UPDATE slots
                SET status = 'booked', booked_by = $1
                WHERE id = $2 AND status = 'available'
                RETURNING id, venue_id, date::TEXT, start_time::TEXT, end_time::TEXT
            """, x_user_id, body.slot_id)

            if not updated:
                slot = await conn.fetchrow(
                    "SELECT id FROM slots WHERE id = $1", body.slot_id
                )
                if not slot:
                    raise HTTPException(status_code=404, detail="Slot not found")
                raise HTTPException(status_code=409, detail="Slot already booked")

            venue = await conn.fetchrow(
                "SELECT name FROM venues WHERE id = $1", updated["venue_id"]
            )

            booking = await conn.fetchrow("""
                INSERT INTO bookings
                    (user_id, slot_id, venue_id, venue_name, date, start_time, end_time)
                VALUES ($1, $2, $3, $4, $5::DATE, $6::TIME, $7::TIME)
                RETURNING
                    id, user_id, slot_id, venue_id, venue_name,
                    date::TEXT, start_time::TEXT, end_time::TEXT,
                    status, created_at::TEXT
            """,
                x_user_id,
                updated["id"],
                updated["venue_id"],
                venue["name"],
                date.fromisoformat(updated["date"]),
                time.fromisoformat(updated["start_time"]),
                time.fromisoformat(updated["end_time"]),
            )

    return dict(booking)


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(
    booking_id: str,
    x_user_id: str = Header(...),
):
    pool = get_pool()
    await _validate_user(x_user_id, pool)

    async with pool.acquire() as conn:
        async with conn.transaction():
            booking = await conn.fetchrow(
                "SELECT user_id, slot_id, status FROM bookings WHERE id = $1",
                booking_id,
            )

            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")

            if booking["user_id"] != x_user_id:
                raise HTTPException(status_code=403, detail="Not your booking")

            if booking["status"] == "cancelled":
                raise HTTPException(status_code=409, detail="Already cancelled")

            await conn.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE id = $1", booking_id
            )
            await conn.execute(
                "UPDATE slots SET status = 'available', booked_by = NULL WHERE id = $1",
                booking["slot_id"],
            )
