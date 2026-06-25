import json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, redis_client
from app.models import Concert, Seat

router = APIRouter(tags=["Concerts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/concerts", response_class=HTMLResponse)
async def list_concerts(request: Request, db: AsyncSession = Depends(get_db)):
    # 1. Пробуємо взяти дані з кешу Redis
    cached_concerts = await redis_client.get("catalog_concerts")

    if cached_concerts:
        print("--- ДАНІ ВЗЯТО З КЕШУ REDIS ---")
        concerts_data = json.loads(cached_concerts)
    else:
        print("--- КЕШ ПОРОЖНІЙ. ЗАПИТ ДО POSTGRESQL ---")
        result = await db.execute(select(Concert))
        concerts = result.scalars().all()

        # КРИТИЧНО: Перетворюємо c.base_price на float, щоб json зміг його серіалізувати!
        concerts_data = [
            {
                "id": c.id,
                "title": c.title,
                "artist": c.artist,
                "genre": c.genre,
                "location": c.location,
                "date_time": c.date_time.isoformat(),
                "base_price": float(c.base_price)  # <-- ОСЬ ТУТ ДОДАЄМО float()
            } for c in concerts
        ]
        # Тепер Redis прийме цей JSON без жодних помилок
        await redis_client.setex("catalog_concerts", 60, json.dumps(concerts_data))

    return templates.TemplateResponse(
        name="concerts.html",
        context={"request": request, "concerts": concerts_data}
    )

@router.get("/concert/{concert_id}/seats", response_class=HTMLResponse)
async def get_seats(concert_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    # Сторінка схеми залу (динамічна, тому без Redis, щоб бачити реальні статуси броні)
    result = await db.execute(select(Seat).where(Seat.concert_id == concert_id))
    seats = result.scalars().all()
    return templates.TemplateResponse(
        name="seats.html",
        context={"request": request, "seats": seats, "concert_id": concert_id}
    )