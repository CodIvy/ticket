from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import engine, Base
from app.scraper import fetch_and_sync_concerts
from app.routes_auth import router as auth_router
from app.routes_concerts import router as concerts_router
from app.routes_booking import router as booking_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Автоматичне створення таблиць на старті
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("--- СХЕМА БАЗИ ДАНИХ УСПІШНО СИНХРОНІЗОВАНА ---")

    # Конфігурація фонового планувальника концертів
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_sync_concerts, 'interval', hours=6)
    scheduler.start()
    print("--- ПЛАНУВАЛЬНИК ФОНОВИХ ЗАВДАНЬ ЗАПУЩЕНО ---")

    # Первинна синхронізація
    await fetch_and_sync_concerts()

    yield
    scheduler.shutdown()
    print("--- ПЛАНУВАЛЬНИК ФОНОВИХ ЗАВДАНЬ ЗУПИНЕНО ---")

app = FastAPI(title="Ticket Booking Service", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(concerts_router)
app.include_router(booking_router)

@app.get("/")
async def root():
    return RedirectResponse(url="/concerts")