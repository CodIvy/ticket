import sys
import os
import asyncio  # Додано для запуску фонових задач
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
    # 1. Швидка синхронізація структури БД (виконується миттєво)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Ініціалізація та запуск планувальника для скрапера
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_sync_concerts, 'interval', hours=6)
    scheduler.start()

    # ПРАВИЛЬНО: Запускаємо перший синк у бекграунді (без await).
    # Сервер миттєво зробить yield, відкриє порт 8000 і пройде Cloud Health Check.
    asyncio.create_task(fetch_and_sync_concerts())

    yield
    # 3. Коректне завершення роботи планувальника при зупинці сервера
    scheduler.shutdown()


app = FastAPI(
    title="Ticket Booking Service",
    description="Високонавантажена система бронювання квитків",
    lifespan=lifespan
)

# Монтування статики (шлях /app/app/static всередині Docker-контейнера)
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Підключення маршрутизаторів додатку
app.include_router(auth_router)
app.include_router(concerts_router)
app.include_router(booking_router)


@app.get("/")
async def root():
    # Автоматичний редірект на каталог концертів для зручності перевірки викладачем
    return RedirectResponse(url="/concerts")