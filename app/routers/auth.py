import re
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from app.database import get_pool
from app.models import UserCreate, UserLogin, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$')


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(body: UserCreate):
    pool = get_pool()
    email = body.email.strip().lower()
    if not email or not body.password or not body.name.strip():
        raise HTTPException(status_code=422, detail="All fields are required")
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if not PASSWORD_REGEX.match(body.password):
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters with letters, numbers, and a symbol")
    existing = await pool.fetchrow("SELECT id FROM users WHERE email = $1", email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = pwd_context.hash(body.password)
    row = await pool.fetchrow("""
        INSERT INTO users (name, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id, name, email
    """, body.name.strip(), email, hashed)
    return AuthResponse(user_id=row["id"], name=row["name"], email=row["email"])


@router.post("/login", response_model=AuthResponse)
async def login(body: UserLogin):
    pool = get_pool()
    user = await pool.fetchrow(
        "SELECT id, name, email, password_hash FROM users WHERE email = $1",
        body.email.strip().lower(),
    )
    if not user or not pwd_context.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResponse(user_id=user["id"], name=user["name"], email=user["email"])
