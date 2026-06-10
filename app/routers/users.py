from fastapi import APIRouter, HTTPException
from app.database import get_pool
from app.models import Booking

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/bookings", response_model=list[Booking])
async def get_user_bookings(user_id: str):
    # TODO: implement
    pass
