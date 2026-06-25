import json
import os
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, redis_client
from app.models import Concert, Seat

router = APIRouter(tags=["Concerts"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/concerts", response_class=HTMLResponse)
async def list_concerts(request: Request, genre: str = None, db: AsyncSession = Depends(get_db)):
    # Зчитуємо ID користувача для динамічного відображення кнопок у шапці
    user_id = request.cookies.get("user_id")

    # 1. Спроба отримати повний каталог із Redis
    cached_concerts = await redis_client.get("catalog_concerts")

    if cached_concerts:
        raw_data = json.loads(cached_concerts)
    else:
        # Якщо кешу немає — йдемо в базу даних PostgreSQL
        result = await db.execute(select(Concert).order_by(Concert.date_time))
        concerts = result.scalars().all()

        # Серіалізуємо дані в примітивні типи для JSON/Redis
        raw_data = [
            {
                "id": c.id,
                "title": c.title,
                "artist": c.artist,
                "genre": c.genre,
                "location": c.location,
                "date_time": c.date_time.isoformat() if c.date_time else None,
                "base_price": float(c.base_price)
            } for c in concerts
        ]
        # Записуємо структуру в кеш на 60 секунд
        await redis_client.setex("catalog_concerts", 60, json.dumps(raw_data))

    # КРИТИЧНИЙ ФІКС: Парсимо ISO-рядки назад в об'єкти datetime для Jinja2
    concerts_data = []
    for item in raw_data:
        concert_dict = item.copy()
        if concert_dict.get("date_time"):
            # Очищаємо від можливих маркерів часових поясів
            dt_str = concert_dict["date_time"].replace("Z", "")
            concert_dict["date_time"] = datetime.fromisoformat(dt_str)
        concerts_data.append(concert_dict)

    # Логіка фільтрації за жанрами (Rock / Pop)
    if genre:
        concerts_data = [c for c in concerts_data if c.get("genre") == genre]

    return templates.TemplateResponse(
        request=request,
        name="catalog.html",
        context={
            "concerts": concerts_data,
            "selected_genre": genre,
            "user_id": user_id
        }
    )


@router.get("/concert/{concert_id}/seats", response_class=HTMLResponse)
async def get_seats(concert_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")

    stmt = (
        select(Seat)
        .where(Seat.concert_id == concert_id)
        .order_by(Seat.row_number, Seat.seat_number)
    )
    result = await db.execute(stmt)
    seats = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="seats.html",
        context={
            "seats": seats,
            "concert_id": concert_id,
            "user_id": user_id
        }
    )