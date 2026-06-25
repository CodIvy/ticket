from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.database import async_session, redis_client
from app.models import Concert, Seat, SeatStatus


async def fetch_and_sync_concerts():
    try:
        now_utc = datetime.now(timezone.utc)

        external_events = [
            {
                "title": "The Rock Legends Tour",
                "artist": "AC/DC (Tribute Show)",
                "genre": "Rock",
                "location": "Київ, Палац Спорту",
                "date": (now_utc + timedelta(days=30)).replace(tzinfo=None).isoformat(),
                "price": 850.00
            },
            {
                "title": "Jazz Evening under the Stars",
                "artist": "Kyiv Jazz Quintet",
                "genre": "Pop",  # Замаплено на Pop для підтримки базових фільтрів вашого UI
                "location": "Київ, Ботанічний сад",
                "date": (now_utc + timedelta(days=15)).replace(tzinfo=None).isoformat(),
                "price": 450.00
            },
            {
                "title": "Вечір Українського Року",
                "artist": "Океан Ельзи (Tribute)",
                "genre": "Rock",
                "location": "Київ, Палац Спорту",
                "date": (now_utc + timedelta(days=5)).replace(tzinfo=None).isoformat(),
                "price": 950.00
            },
            {
                "title": "Поп Хіти Твого Літа",
                "artist": "Макс Барських (Cover Show)",
                "genre": "Pop",
                "location": "Київ, Клуб Атлас",
                "date": (now_utc + timedelta(days=8)).replace(tzinfo=None).isoformat(),
                "price": 600.00
            },
            {
                "title": "Симфонічний Рок Шторм",
                "artist": "Lords of the Sound",
                "genre": "Rock",
                "location": "Київ, Жовтневий Палац",
                "date": (now_utc + timedelta(days=12)).replace(tzinfo=None).isoformat(),
                "price": 1200.00
            },
            {
                "title": "Акустичний Вечір",
                "artist": "Один в Каное (Cover)",
                "genre": "Pop",
                "location": "Київ, Bel etage",
                "date": (now_utc + timedelta(days=18)).replace(tzinfo=None).isoformat(),
                "price": 500.00
            },
            {
                "title": "Грандіозний Рок-Марафон",
                "artist": "Без Обмежень (Best Hits)",
                "genre": "Rock",
                "location": "Київ, Стереоплаза",
                "date": (now_utc + timedelta(days=22)).replace(tzinfo=None).isoformat(),
                "price": 700.00
            },
            {
                "title": "Поп Королева Вечора",
                "artist": "Оля Полякова (Cover Night)",
                "genre": "Pop",
                "location": "Київ, Палац Спорту",
                "date": (now_utc + timedelta(days=25)).replace(tzinfo=None).isoformat(),
                "price": 800.00
            },
            {
                "title": "Легенди Західного Металу",
                "artist": "The Hardkiss (Tribute Event)",
                "genre": "Rock",
                "location": "Київ, Клуб Атлас",
                "date": (now_utc + timedelta(days=28)).replace(tzinfo=None).isoformat(),
                "price": 750.00
            },
            {
                "title": "Інді-Поп Хвиля",
                "artist": "Latexfauna (Tribute Night)",
                "genre": "Pop",
                "location": "Київ, Bel etage",
                "date": (now_utc + timedelta(days=32)).replace(tzinfo=None).isoformat(),
                "price": 550.00
            },
            {
                "title": "Енергія Українського Панку",
                "artist": "Жадан і Собаки (Cover)",
                "genre": "Rock",
                "location": "Київ, Стереоплаза",
                "date": (now_utc + timedelta(days=35)).replace(tzinfo=None).isoformat(),
                "price": 480.00
            },
            {
                "title": "Танцювальний Поп-Рейв",
                "artist": "Monatik (Tribute Show)",
                "genre": "Pop",
                "location": "Київ, Палац Спорту",
                "date": (now_utc + timedelta(days=38)).replace(tzinfo=None).isoformat(),
                "price": 900.00
            },
            {
                "title": "Рок-Балади під гітару",
                "artist": "Скрябін (Вечір Пам'яті)",
                "genre": "Rock",
                "location": "Київ, Жовтневий Палац",
                "date": (now_utc + timedelta(days=42)).replace(tzinfo=None).isoformat(),
                "price": 650.00
            },
            {
                "title": "Сучасний Музичний Пульс",
                "artist": "Артем Пивоваров (Cover Night)",
                "genre": "Pop",
                "location": "Київ, Стереоплаза",
                "date": (now_utc + timedelta(days=45)).replace(tzinfo=None).isoformat(),
                "price": 1100.00
            },
            {
                "title": "Класика Альтернативного Року",
                "artist": "Друга Ріка (Акустика)",
                "genre": "Rock",
                "location": "Київ, Жовтневий Палац",
                "date": (now_utc + timedelta(days=48)).replace(tzinfo=None).isoformat(),
                "price": 700.00
            },
            {
                "title": "Нічний Поп-Драйв",
                "artist": "Дорофєєва (Best Hits)",
                "genre": "Pop",
                "location": "Київ, Клуб Атлас",
                "date": (now_utc + timedelta(days=50)).replace(tzinfo=None).isoformat(),
                "price": 850.00
            },
            {
                "title": "Важкий Етно-Рок",
                "artist": "Карна (Tribute Party)",
                "genre": "Rock",
                "location": "Київ, Bel etage",
                "date": (now_utc + timedelta(days=52)).replace(tzinfo=None).isoformat(),
                "price": 400.00
            },
            {
                "title": "Ліричний Поп Вечір",
                "artist": "KOLA (Cover Event)",
                "genre": "Pop",
                "location": "Київ, Жовтневий Палац",
                "date": (now_utc + timedelta(days=55)).replace(tzinfo=None).isoformat(),
                "price": 650.00
            },
            {
                "title": "Андеграунд Рок Клуб",
                "artist": "Мотор'ролла (Tribute)",
                "genre": "Rock",
                "location": "Київ, Клуб Атлас",
                "date": (now_utc + timedelta(days=58)).replace(tzinfo=None).isoformat(),
                "price": 350.00
            },
            {
                "title": "Акустичний Поп Вечір",
                "artist": "Jerry Heil (Cover Show)",
                "genre": "Pop",
                "location": "Київ, Ботанічний сад",
                "date": (now_utc + timedelta(days=60)).replace(tzinfo=None).isoformat(),
                "price": 600.00
            }
        ]

        async with async_session() as session:
            async with session.begin():
                cache_invalidated = False

                for event in external_events:
                    stmt = select(Concert).where(Concert.title == event["title"])
                    result = await session.execute(stmt)
                    existing_concert = result.scalar_one_or_none()

                    if not existing_concert:
                        new_concert = Concert(
                            title=event["title"],
                            artist=event["artist"],
                            genre=event["genre"],
                            location=event["location"],
                            date_time=datetime.fromisoformat(event["date"]),
                            base_price=event["price"]
                        )
                        session.add(new_concert)
                        await session.flush()

                        seats_to_create = [
                            Seat(
                                concert_id=new_concert.id,
                                row_number=row,
                                seat_number=seat_num,
                                status=SeatStatus.FREE
                            )
                            for row in range(1, 5)
                            for seat_num in range(1, 11)
                        ]
                        session.add_all(seats_to_create)
                        cache_invalidated = True

                if cache_invalidated:
                    await redis_client.delete("catalog_concerts")

    except Exception as e:
        pass