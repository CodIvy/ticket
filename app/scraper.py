from datetime import datetime, timedelta
from sqlalchemy import select

from app.database import async_session, redis_client
from app.models import Concert, Seat, SeatStatus


# Шаблон адреси для майбутньої інтеграції (наразі закоментований)
# EXTERNAL_API_URL = "https://api.concerts-provider.com/v1/events"

async def fetch_and_sync_concerts():
    """
    Фонове завдання для автоматичного наповнення бази даних актуальними концертами.
    Працює автономно при старті додатка та періодично через APScheduler.
    """
    print(f"[{datetime.now()}] --- ЗАПУСК АВТОМАТИЧНОГО ОНОВЛЕННЯ КОНЦЕРТІВ ---")

    try:
        # Етап 1: Імітація отримання свіжих даних з інтернету (Mock-дані)
        # Коли підключатимете справжнє API, тут буде блок:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(EXTERNAL_API_URL, timeout=10.0)
        #     external_events = response.json().get("events", [])

        external_events = [
            {
                "title": "The Rock Legends Tour",
                "artist": "AC/DC (Tribute Show)",
                "genre": "Rock",
                "location": "Київ, Палац Спорту",
                "date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "price": 850.00
            },
            {
                "title": "Jazz Evening under the Stars",
                "artist": "Kyiv Jazz Quintet",
                "genre": "Jazz",
                "location": "Київ, Ботанічний сад",
                "date": (datetime.utcnow() + timedelta(days=15)).isoformat(),
                "price": 450.00
            }
        ]

        # Етап 2: Синхронізація з PostgreSQL
        async with async_session() as session:
            # Відкриваємо атомарну транзакцію для безпечного запису даних
            async with session.begin():
                for event in external_events:
                    # Перевіряємо за назвою, чи цей концерт вже імпортовано раніше
                    stmt = select(Concert).where(Concert.title == event["title"])
                    result = await session.execute(stmt)
                    existing_concert = result.scalar_one_or_none()

                    if not existing_concert:
                        print(f"Скрейпер знайшов новий концерт: '{event['title']}'")

                        # Створюємо запис концерту
                        new_concert = Concert(
                            title=event["title"],
                            artist=event["artist"],
                            genre=event["genre"],
                            location=event["location"],
                            date_time=datetime.fromisoformat(event["date"]),
                            base_price=event["price"]
                        )
                        session.add(new_concert)
                        await session.flush()  # Фіксуємо об'єкт у базі, щоб згенерувався new_concert.id

                        # Автоматично генеруємо інтерактивну сітку місць для залу (4 ряди по 10 місць)
                        for row in range(1, 5):
                            for seat_num in range(1, 11):
                                session.add(Seat(
                                    concert_id=new_concert.id,
                                    row_number=row,
                                    seat_number=seat_num,
                                    status=SeatStatus.FREE
                                ))
                        print(f"Створено 40 квитків для концерту ID: {new_concert.id}")

                # Етап 3: Інвалідація кешу в Redis
                # Якщо з'явилися нові концерти, старий кеш головної сторінки стає неактуальним.
                # Видаляємо ключ, і наступний користувач отримає вже оновлений список з бази.
                await redis_client.delete("catalog_concerts")
                print("--- СИНХРОНІЗАЦІЮ ЗАВЕРШЕНО, КЕШ REDIS ОЧИЩЕНО ---")

    except Exception as e:
        print(f"Помилка під час автоматичної синхронізації скрейпера: {e}")