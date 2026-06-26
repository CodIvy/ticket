import sys
import os
import asyncio  # For updating and scraping(unrealised too much work maybe in future)
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
    # DB synchronisation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Scraper ini(not really i just use generated list)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_sync_concerts, 'interval', hours=6)
    scheduler.start()

    asyncio.create_task(fetch_and_sync_concerts())

    yield
    scheduler.shutdown()


app = FastAPI(
    title="Ticket Booking Service",
    description="Високонавантажена система бронювання квитків",
    lifespan=lifespan
)

# Static for good webview as recomennded in internet
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routers for differnt pages
app.include_router(auth_router)
app.include_router(concerts_router)
app.include_router(booking_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/concerts")