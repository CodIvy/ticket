import os
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


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

    new_user = User(email=email, password_hash=hash_password(password))
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