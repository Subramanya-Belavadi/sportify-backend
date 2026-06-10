from pydantic import BaseModel
from typing import Optional


# --- Venue ---
class Venue(BaseModel):
    id: str
    name: str
    address: str
    sport: str
    image_url: Optional[str] = ""
    price_per_hour: float


# --- Slot ---
class Slot(BaseModel):
    id: str
    venue_id: str
    date: str
    start_time: str
    end_time: str
    status: str  # 'available' | 'booked'
    booked_by: Optional[str] = None


# --- Booking ---
class BookingRequest(BaseModel):
    slot_id: str
    user_id: str


class Booking(BaseModel):
    id: str
    user_id: str
    slot_id: str
    venue_id: str
    venue_name: str
    date: str
    start_time: str
    end_time: str
    status: str
    created_at: str
