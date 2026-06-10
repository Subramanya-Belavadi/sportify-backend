from fastapi import APIRouter, HTTPException, Header
from app.database import get_pool
from app.models import BookingRequest, Booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=Booking, status_code=201)
async def book_slot(body: BookingRequest, x_user_id: str = Header(...)):
    # TODO: implement — atomic UPDATE, return 409 if slot already taken
    pass


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(booking_id: str, x_user_id: str = Header(...)):
    # TODO: implement
    pass
