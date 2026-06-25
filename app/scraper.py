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
                "genre": "Jazz",
                "location": "Київ, Ботанічний сад",
                "date": (now_utc + timedelta(days=15)).replace(tzinfo=None).isoformat(),
                "price": 450.00
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