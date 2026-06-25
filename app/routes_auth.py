from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_user(
        response: Response,
        email: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    async with db.begin():
        # Перевіряємо, чи є вже такий email
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Користувач з таким Email вже існує")

        # Хешуємо пароль через новий швидкий bcrypt
        new_user = User(email=email, password_hash=hash_password(password))
        db.add(new_user)
        await db.flush()  # Отримуємо ID користувача

        # Автоматично логінимо після реєстрації — записуємо куку сесії
        redirect = RedirectResponse(url="/concerts", status_code=303)
        redirect.set_cookie(key="user_id", value=str(new_user.id), httponly=True, max_age=3600)
        return redirect


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_user(
        email: str = Form(...),
        password: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неправильний Email або пароль")

    # Успішний вхід
    redirect = RedirectResponse(url="/concerts", status_code=303)
    redirect.set_cookie(key="user_id", value=str(user.id), httponly=True, max_age=3600)
    return redirect


@router.get("/logout")
async def logout_user():
    # Очищення сесії
    redirect = RedirectResponse(url="/auth/login", status_code=303)
    redirect.delete_cookie(key="user_id")
    return redirect