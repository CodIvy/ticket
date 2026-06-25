import os
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ticket_user:1234@127.0.0.1:5432/ticket_service_db"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Вимкнено логування SQL-запитів, оскільки воно сильно гальмує I/O під час стрес-тестів
    pool_size=50,  # Збільшено базовий пул під велику кількість паралельних з'єднань k6
    max_overflow=50,  # Загальний ліміт з'єднань доведено до 100
    pool_timeout=30.0,  # Зменшено таймаут, щоб швидше звільняти застряглі запити
    pool_pre_ping=True  # Автоматична перевірка «життя» з'єднання перед використанням
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with async_session() as session:
        yield session

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)