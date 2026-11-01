"""Modelo de datos (capa de datos)."""
import enum
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"  # v1.1: el cliente asistió (genera puntos)


class NotificationType(str, enum.Enum):
    CONFIRMATION = "CONFIRMATION"
    MODIFICATION = "MODIFICATION"
    CANCELLATION = "CANCELLATION"
    REWARD = "REWARD"          # v1.1: puntos ganados
    REDEMPTION = "REDEMPTION"  # v1.1: canje de puntos


class RewardType(str, enum.Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20))
    opening_time: Mapped[time] = mapped_column(Time)
    closing_time: Mapped[time] = mapped_column(Time)

    tables: Mapped[list["Table"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    number: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(50), default="Salón")

    restaurant: Mapped[Restaurant] = relationship(back_populates="tables")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # v1.1 - programa de recompensas
    points: Mapped[int] = mapped_column(Integer, default=0)           # saldo canjeable
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0)  # acumulado histórico (define el nivel)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="customer")
    reward_transactions: Mapped[list["RewardTransaction"]] = relationship(back_populates="customer")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    party_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    customer: Mapped[Customer] = relationship(back_populates="reservations")
    restaurant: Mapped[Restaurant] = relationship()
    table: Mapped[Table] = relationship()
    notifications: Mapped[list["Notification"]] = relationship(back_populates="reservation")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # v1.1: nullable, porque las notificaciones de canje no pertenecen a una reserva
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    channel: Mapped[str] = mapped_column(String(20), default="EMAIL")
    recipient: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="SENT")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    reservation: Mapped[Reservation | None] = relationship(back_populates="notifications")
    customer: Mapped[Customer] = relationship()


class RewardTransaction(Base):
    """v1.1: movimiento de puntos (ganancia por reserva completada o canje)."""
    __tablename__ = "reward_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), nullable=True, unique=True)
    type: Mapped[RewardType] = mapped_column(Enum(RewardType))
    points: Mapped[int] = mapped_column(Integer)  # positivo al ganar, negativo al canjear
    description: Mapped[str] = mapped_column(String(200))
    coupon_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    customer: Mapped[Customer] = relationship(back_populates="reward_transactions")
