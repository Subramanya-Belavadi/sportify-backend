from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import connect_db, disconnect_db
from app.routers import venues, bookings, users, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(title="Sportify API", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(venues.router)
app.include_router(bookings.router)
app.include_router(users.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
