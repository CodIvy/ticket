import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, Numeric, DateTime, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class SeatStatus(str, enum.Enum):
    FREE = "FREE"
    BOOKED = "BOOKED"
    SOLD = "SOLD"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Concert(Base):
    __tablename__ = "concerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concert_id: Mapped[int] = mapped_column(
        ForeignKey("concerts.id", ondelete="CASCADE"),
        nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SeatStatus] = mapped_column(Enum(SeatStatus), default=SeatStatus.FREE)
    reserved_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reserved_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("concert_id", "row_number", "seat_number", name="uq_concert_seat"),
        Index("idx_seats_concert_status", "concert_id", "status"), # Прискорює вибірку вільних місць під навантаженням
    )

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="RESTRICT"), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))