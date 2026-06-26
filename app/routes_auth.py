import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Order, Seat, Concert
from app.auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

#Особистий кабінет з регістрацією та логіном все+- інтуітивне і краще не трогати
#(ця частина кода за весь час розробки видавала найменше ошибок)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


@router.post("/register")
async def register_user(
        email: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email вже зайнятий")

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    new_user = User(
        email=email,
        password_hash=hash_password(password),
        created_at=now_naive
    )
    db.add(new_user)
    await db.commit()

    redirect = RedirectResponse(url="/concerts", status_code=303)
    redirect.set_cookie(key="user_id", value=str(new_user.id), httponly=True)
    return redirect


@router.post("/login")
async def login_user(
        email: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неправильний email або пароль")

    redirect = RedirectResponse(url="/concerts", status_code=303)
    redirect.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return redirect


@router.get("/logout")
async def logout_user():
    redirect = RedirectResponse(url="/auth/login", status_code=303)
    redirect.delete_cookie(key="user_id")
    return redirect


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

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

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
            "date": concert.date_time.strftime("%d.%m.%Y %H:%M") if concert.date_time else "",
            "row": seat.row_number,
            "seat": seat.seat_number,
            "amount": float(order.amount_paid),
            "purchased_at": order.purchased_at.strftime("%d.%m.%Y %H:%M") if order.purchased_at else ""
        })

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "history": history}
    )