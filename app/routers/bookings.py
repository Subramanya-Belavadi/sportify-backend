from fastapi import APIRouter, HTTPException, Header
from app.database import get_pool
from app.models import BookingRequest, Booking

router = APIRouter(prefix="/bookings", tags=["bookings"])

VALID_USERS = {"user_1", "user_2", "user_3"}


@router.post("", response_model=Booking, status_code=201)
async def book_slot(
    body: BookingRequest,
    x_user_id: str = Header(..., description="Hardcoded user ID"),
):
    if x_user_id not in VALID_USERS:
        raise HTTPException(status_code=401, detail="Invalid user")

    if body.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Atomic UPDATE — this is the concurrency-safe booking pattern.
            # Only one transaction can update a row at a time in PostgreSQL.
            # If two requests arrive simultaneously, one wins and the other
            # finds 0 rows updated (status is already 'booked').
            updated = await conn.fetchrow("""
                UPDATE slots
                SET status = 'booked', booked_by = $1
                WHERE id = $2 AND status = 'available'
                RETURNING id, venue_id, date::TEXT, start_time::TEXT, end_time::TEXT
            """, x_user_id, body.slot_id)

            if not updated:
                # Either slot doesn't exist or already booked
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
                updated["date"],
                updated["start_time"],
                updated["end_time"],
            )

    return dict(booking)


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(
    booking_id: str,
    x_user_id: str = Header(...),
):
    if x_user_id not in VALID_USERS:
        raise HTTPException(status_code=401, detail="Invalid user")

    pool = get_pool()

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
