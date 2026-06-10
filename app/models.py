from pydantic import BaseModel
from typing import Optional


class Venue(BaseModel):
    id: str
    name: str
    address: str
    sport: str
    image_url: Optional[str] = ""
    price_per_hour: float

    model_config = {"from_attributes": True}


class Slot(BaseModel):
    id: str
    venue_id: str
    date: str
    start_time: str
    end_time: str
    status: str  # 'available' | 'booked'
    booked_by: Optional[str] = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    name: str
    email: str


GST_RATE = 0.18


class BookingRequest(BaseModel):
    slot_id: str
    user_id: str
    duration_hours: int = 1


class Booking(BaseModel):
    id: str
    user_id: str
    slot_id: str       # first_slot_id aliased for Flutter compatibility
    venue_id: str
    venue_name: str
    date: str
    start_time: str
    end_time: str
    duration_hours: int
    base_amount: float
    gst_amount: float
    total_amount: float
    status: str
    created_at: str

    model_config = {"from_attributes": True}
