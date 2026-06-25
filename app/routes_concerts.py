import json
import os
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
async def list_concerts(request: Request, db: AsyncSession = Depends(get_db)):
    cached_concerts = await redis_client.get("catalog_concerts")

    if cached_concerts:
        concerts_data = json.loads(cached_concerts)
    else:
        result = await db.execute(select(Concert).order_by(Concert.date_time))
        concerts = result.scalars().all()

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
        await redis_client.setex("catalog_concerts", 60, json.dumps(concerts_data))

    return templates.TemplateResponse(
        request=request,
        name="catalog.html",
        context={"concerts": concerts_data}
    )


@router.get("/concert/{concert_id}/seats", response_class=HTMLResponse)
async def get_seats(concert_id: int, request: Request, db: AsyncSession = Depends(get_db)):
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