import json
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, redis_client
from app.models import Concert, Seat

router = APIRouter(tags=["Concerts"])

# ВИПРАВЛЕНО: Шлях адаптовано під робочу директорію Docker-контейнера
templates = Jinja2Templates(directory="templates")


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
                "base_price": float(c.base_price)
            } for c in concerts
        ]
        # Тепер Redis прийме цей JSON без жодних помилок
        await redis_client.setex("catalog_concerts", 60, json.dumps(concerts_data))

    # ВИПРАВЛЕНО: Чиста передача аргументів без дублювання request всередині context
    return templates.TemplateResponse(
        request=request,
        name="concerts.html",
        context={"concerts": concerts_data}
    )


@router.get("/concert/{concert_id}/seats", response_class=HTMLResponse)
async def get_seats(concert_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    # Сторінка схеми залу (динамічна, тому без Redis, щоб бачити реальні статуси броні)

    # ВИПРАВЛЕНО: Додано сортування .order_by(), щоб сітка залу завжди була стабільною
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
        context={"seats": seats, "concert_id": concert_id}
    )