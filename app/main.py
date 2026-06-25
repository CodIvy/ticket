import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))

from app.database import engine, Base
from app.scraper import fetch_and_sync_concerts
from app.routes_auth import router as auth_router
from app.routes_concerts import router as concerts_router
from app.routes_booking import router as booking_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_sync_concerts, 'interval', hours=6)
    scheduler.start()

    await fetch_and_sync_concerts()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Ticket Booking Service",
    description="Високонавантажена система бронювання квитків",
    lifespan=lifespan
)

STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth_router)
app.include_router(concerts_router)
app.include_router(booking_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/concerts")