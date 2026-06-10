from datetime import date, time
from fastapi import APIRouter, HTTPException, Header
from app.database import get_pool
from app.models import BookingRequest, Booking, GST_RATE

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def _validate_user(x_user_id: str, pool) -> None:
    user = await pool.fetchrow("SELECT id FROM users WHERE id = $1", x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")


def _parse_slot_hour(slot_id: str) -> int:
    """Extract hour from slot id pattern: venueId_YYYY-MM-DD_HH"""
    return int(slot_id.rsplit("_", 1)[-1])


def _make_slot_id(first_slot_id: str, offset: int) -> str:
    """Build slot id for hour = base_hour + offset"""
    prefix = first_slot_id.rsplit("_", 1)[0]
    base_hour = _parse_slot_hour(first_slot_id)
    return f"{prefix}_{base_hour + offset:02d}"


@router.post("", response_model=Booking, status_code=201)
async def book_slot(
    body: BookingRequest,
    x_user_id: str = Header(..., description="User ID from login"),
):
    if body.duration_hours < 1 or body.duration_hours > 4:
        raise HTTPException(status_code=422, detail="Duration must be between 1 and 4 hours")

    pool = get_pool()
    await _validate_user(x_user_id, pool)

    slot_ids = [_make_slot_id(body.slot_id, i) for i in range(body.duration_hours)]

    # Derive start/end time from slot_id to check for user overlap
    base_hour = _parse_slot_hour(body.slot_id)
    requested_start = time(base_hour, 0)
    requested_end = time(base_hour + body.duration_hours, 0)
    slot_date_str = body.slot_id.rsplit("_", 2)[1]  # venueId_YYYY-MM-DD_HH
    requested_date = date.fromisoformat(slot_date_str)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Reject if user already has a confirmed booking that overlaps this time window
            conflict = await conn.fetchval("""
                SELECT COUNT(*) FROM bookings
                WHERE user_id = $1
                  AND date = $2
                  AND status = 'confirmed'
                  AND start_time < $4
                  AND end_time > $3
            """, x_user_id, requested_date, requested_start, requested_end)

            if conflict > 0:
                raise HTTPException(
                    status_code=409,
                    detail="You already have a booking that overlaps this time slot"
                )

            # Atomically book all consecutive slots (available OR reserved by same user)
            updated = await conn.fetch("""
                UPDATE slots SET status = 'booked', booked_by = $1,
                                 reserved_by = NULL, reserved_until = NULL
                WHERE id = ANY($2::text[])
                  AND (status = 'available'
                       OR (status = 'reserved' AND reserved_by = $1))
                RETURNING id, venue_id, date::TEXT, start_time::TEXT, end_time::TEXT
            """, x_user_id, slot_ids)

            if len(updated) != body.duration_hours:
                # Some slots not available — rollback happens automatically
                raise HTTPException(status_code=409, detail="One or more slots are already booked")

            # Sort by start_time to get correct first/last
            updated_sorted = sorted(updated, key=lambda r: r["start_time"])
            first = updated_sorted[0]
            last = updated_sorted[-1]

            venue = await conn.fetchrow(
                "SELECT name, price_per_hour FROM venues WHERE id = $1", first["venue_id"]
            )

            base_amount = float(venue["price_per_hour"]) * body.duration_hours
            gst_amount = round(base_amount * GST_RATE, 2)
            total_amount = round(base_amount + gst_amount, 2)

            booking = await conn.fetchrow("""
                INSERT INTO bookings
                    (user_id, first_slot_id, venue_id, venue_name, date, start_time, end_time,
                     duration_hours, base_amount, gst_amount, total_amount)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING
                    id, user_id, first_slot_id AS slot_id, venue_id, venue_name,
                    date::TEXT, start_time::TEXT, end_time::TEXT,
                    duration_hours, base_amount, gst_amount, total_amount,
                    status, created_at::TEXT
            """,
                x_user_id,
                first["id"],
                first["venue_id"],
                venue["name"],
                date.fromisoformat(first["date"]),
                time.fromisoformat(first["start_time"]),
                time.fromisoformat(last["end_time"]),
                body.duration_hours,
                base_amount,
                gst_amount,
                total_amount,
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
                """SELECT user_id, first_slot_id, duration_hours, status
                   FROM bookings WHERE id = $1""",
                booking_id,
            )

            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if booking["user_id"] != x_user_id:
                raise HTTPException(status_code=403, detail="Not your booking")
            if booking["status"] == "cancelled":
                raise HTTPException(status_code=409, detail="Already cancelled")

            # Free all booked slots
            slot_ids = [
                _make_slot_id(booking["first_slot_id"], i)
                for i in range(booking["duration_hours"])
            ]
            await conn.execute(
                "UPDATE slots SET status = 'available', booked_by = NULL WHERE id = ANY($1::text[])",
                slot_ids,
            )
            await conn.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE id = $1", booking_id
            )
