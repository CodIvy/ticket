import os
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import Seat, Concert, SeatStatus, Order

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="/concert", tags=["Booking"])


@router.post("/book")
async def book_seat(
        request: Request,
        seat_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    user_id_raw = request.cookies.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw else None
    except ValueError:
        user_id = None

    query = select(Seat).where(Seat.id == seat_id).with_for_update()
    result = await db.execute(query)
    seat = result.scalar_one_or_none()

    if not seat:
        raise HTTPException(status_code=404, detail="Місце не знайдено")

    now = datetime.now(timezone.utc)

    if seat.reserved_until and seat.reserved_until.tzinfo is None:
        now = now.replace(tzinfo=None)
    elif seat.reserved_until is None:
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
@router.get("/payment-page/{seat_id}", response_class=HTMLResponse)
async def payment_page(seat_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    # 1. Отримуємо місце
    query_seat = select(Seat).where(Seat.id == seat_id)
    result_seat = await db.execute(query_seat)
    seat = result_seat.scalar_one_or_none()

    if not seat:
        raise HTTPException(status_code=404, detail="Місце не знайдено")

    # 2. Додано: Отримуємо концерт, пов'язаний із цим місцем
    query_concert = select(Concert).where(Concert.id == seat.concert_id)
    result_concert = await db.execute(query_concert)
    concert = result_concert.scalar_one_or_none()

    if not concert:
        raise HTTPException(status_code=404, detail="Концерт не знайдено")

    # 3. Передаємо обидва об'єкти в шаблон
    return templates.TemplateResponse(
        request=request,
        name="payment.html",
        context={"seat": seat, "concert": concert} # Тепер змінна 'concert' доступна у шаблоні
    )


@router.post("/pay")
async def process_payment(
        request: Request,
        seat_id: int = Form(...),
        db: AsyncSession = Depends(get_db)
):
    """Обробка успішної оплати квитка"""
    # 1. Шукаємо місце та блокуємо рядок для уникнення race conditions
    query = select(Seat).where(Seat.id == seat_id).with_for_update()
    result = await db.execute(query)
    seat = result.scalar_one_or_none()

    if not seat:
        raise HTTPException(status_code=404, detail="Місце не знайдено")

    # 2. Отримуємо ID користувача з кук
    user_id_raw = request.cookies.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw else None
    except ValueError:
        user_id = None

    # 3. Перевіряємо, чи місце дійсно заброньоване цим користувачем (або анонімом)
    if seat.status != SeatStatus.BOOKED:
        raise HTTPException(status_code=400, detail="Місце не заброньоване або вже викуплене")

    # 4. Отримуємо ціну концерту для фіксації суми в замовленні
    query_concert = select(Concert).where(Concert.id == seat.concert_id)
    result_concert = await db.execute(query_concert)
    concert = result_concert.scalar_one_or_none()

    amount = float(concert.base_price) if concert else 0.0

    # 5. Змінюємо статус місця на SOLD та очищаємо таймер броні
    seat.status = SeatStatus.SOLD
    seat.reserved_until = None

    # 6. Фіксуємо фінансове замовлення, якщо користувач авторизований
    if user_id:
        new_order = Order(
            user_id=user_id,
            seat_id=seat.id,
            amount_paid=amount
        )
        db.add(new_order)

    await db.commit()

    # Після успішної оплати повертаємо користувача на головну сторінку каталогів
    return RedirectResponse(url="/concerts", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Особистий кабінет користувача з історією покупок"""
    user_id_raw = request.cookies.get("user_id")
    if not user_id_raw:
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 1. Отримуємо дані користувача
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 2. Отримуємо історію замовлень разом із деталями квитків та концертів
    # Використовуємо JOIN, щоб дістати все одним швидким запитом під навантаженням
    stmt = (
        select(Order, Seat, Concert)
        .join(Seat, Order.seat_id == Seat.id)
        .join(Concert, Seat.concert_id == Concert.id)
        .where(Order.user_id == user_id)
        .order_by(Order.purchased_at.desc())
    )
    orders_result = await db.execute(stmt)

    history = []
    for order, seat, concert in orders_result:
        history.append({
            "order_id": order.id,
            "concert_title": concert.title,
            "artist": concert.artist,
            "date": concert.date_time.strftime("%d.%m.%Y %H:%M"),
            "row": seat.row_number,
            "seat": seat.seat_number,
            "amount": float(order.amount_paid),
            "purchased_at": order.purchased_at.strftime("%d.%m.%Y %H:%M")
        })

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "history": history}
    )