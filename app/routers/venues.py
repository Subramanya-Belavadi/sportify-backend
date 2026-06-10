from fastapi import APIRouter, HTTPException
from app.database import get_pool
from app.models import Venue, Slot

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=list[Venue])
async def list_venues():
    # TODO: implement
    pass


@router.get("/{venue_id}/slots", response_model=list[Slot])
async def get_slots(venue_id: str, date: str):
    # TODO: implement — date format YYYY-MM-DD
    pass
