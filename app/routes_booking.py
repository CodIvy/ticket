from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Seat, SeatStatus

router = APIRouter(prefix="/concert", tags=["Booking"])


@router.post("/book", response_class=HTMLResponse)
async def book_seat(
        request: Request,
        seat_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    # Витягуємо куку бота або поточного юзера
    user_id = request.cookies.get("user_id")
    user_id = int(user_id) if user_id else 999

    # Відкриваємо атомарну транзакцію
    async with db.begin():
        # Блокуємо рядок на рівні бази даних (FOR UPDATE)
        query = select(Seat).where(Seat.id == seat_id).with_for_update()
        result = await db.execute(query)
        seat = result.scalar_one_or_none()

        if not seat:
            raise HTTPException(status_code=404, detail="Місце не знайдено")

        # Перевірка статусу (враховуючи прострочену бронь)
        now = datetime.utcnow()
        is_free = (seat.status == SeatStatus.FREE) or (
                seat.status == SeatStatus.BOOKED and seat.reserved_until and seat.reserved_until < now
        )

        if not is_free:
            # Всі конкуренти, що стали в чергу, отримають цей статус
            raise HTTPException(status_code=409, detail="Місце вже зайняте")

        # Оновлюємо дані
        seat.status = SeatStatus.BOOKED
        seat.reserved_by_user_id = user_id
        seat.reserved_until = now + timedelta(minutes=10)

        # Після виходу з блоку `async with` SQLAlchemy автоматично робить COMMIT
        # і миттєво відпускає підключення назад у пул.

    return RedirectResponse(url=f"/concert/payment-page/{seat_id}", status_code=303)