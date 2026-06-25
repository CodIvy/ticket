import os
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import Seat, SeatStatus

router = APIRouter(prefix="/concert", tags=["Booking"])


@router.post("/book")
async def book_seat(
        request: Request,
        seat_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    user_id_raw = request.cookies.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw else 999
    except ValueError:
        user_id = 999

    query = select(Seat).where(Seat.id == seat_id).with_for_update()
    result = await db.execute(query)
    seat = result.scalar_one_or_none()

    if not seat:
        raise HTTPException(status_code=404, detail="Місце не знайдено")

    now = datetime.now(timezone.utc)

    if seat.date_time and seat.date_time.tzinfo is None:
        now = now.replace(tzinfo=None)

    is_free = (seat.status == SeatStatus.FREE) or (
            seat.status == SeatStatus.BOOKED and seat.reserved_until and seat.reserved_until < now
    )

    if not is_free:
        raise HTTPException(status_code=409, detail="Місце вже зайняте")

    seat.status = SeatStatus.BOOKED
    seat.reserved_by_user_id = user_id
    seat.reserved_until = now + timedelta(minutes=10)

    await db.commit()

    return RedirectResponse(url=f"/concert/payment-page/{seat_id}", status_code=303)