"""Esquemas Pydantic (validación de entrada y salida de la API)."""
import datetime as dt
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import NotificationType, ReservationStatus, RewardType

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9 ]{6,15}$")


def _check_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value):
        raise ValueError("Correo electrónico inválido")
    return value


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: int
    capacity: int
    location: str


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str
    phone: str
    opening_time: dt.time
    closing_time: dt.time
    max_capacity: int


class AvailabilityOut(BaseModel):
    available: bool
    table: Optional[TableOut] = None
    message: str


class ReservationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    phone: str
    restaurant_id: int
    date: dt.date
    time: dt.time
    party_size: int = Field(ge=1)
    notes: str = Field(default="", max_length=500)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _check_email(v)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("Teléfono inválido")
        return v


class ReservationUpdate(BaseModel):
    email: str
    restaurant_id: Optional[int] = None
    date: Optional[dt.date] = None
    time: Optional[dt.time] = None
    party_size: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _check_email(v)


class OwnerCheck(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _check_email(v)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    status: ReservationStatus
    restaurant_id: int
    restaurant_name: str
    table_number: int
    table_capacity: int
    customer_name: str
    customer_email: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    party_size: int
    notes: str
    created_at: dt.datetime
    updated_at: dt.datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: NotificationType
    channel: str
    recipient: str
    subject: str
    message: str
    status: str
    sent_at: dt.datetime


# ---------- v1.1: programa de recompensas ----------
class RewardTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: RewardType
    points: int
    description: str
    coupon_code: Optional[str] = None
    created_at: dt.datetime


class RewardSummaryOut(BaseModel):
    customer_name: str
    email: str
    points: int
    lifetime_points: int
    level: str
    next_level: Optional[str]
    points_to_next_level: int
    redeem_cost: int
    can_redeem: bool
    transactions: list[RewardTransactionOut]


class CompletionOut(BaseModel):
    code: str
    status: ReservationStatus
    points_earned: int
    customer_points: int
    customer_level: str


class RedemptionOut(BaseModel):
    coupon_code: str
    points_spent: int
    remaining_points: int
    benefit: str
