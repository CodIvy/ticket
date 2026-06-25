import os
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Якщо додаток в Docker — беремо URL з оточення, якщо локально — йдемо на 127.0.0.1
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ticket_user:1234@127.0.0.1:5432/ticket_service_db"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

# Налаштування інжину з максимальним запасом міцності
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,          # Базові підключення
    max_overflow=100,      # Додаткові слоти під піковим навантаженням
    pool_timeout=60.0      # Час очікування в черзі пулу
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session

# Асинхронний клієнт Redis для кешування каталогу
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)