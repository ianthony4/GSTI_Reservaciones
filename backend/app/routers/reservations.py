"""Endpoints de reservas (RF-03 a RF-09)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (NotificationOut, OwnerCheck, ReservationCreate, ReservationOut,
                       ReservationUpdate)
from ..services.reservations import ReservationService
from .common import to_out

router = APIRouter(prefix="/api/reservations", tags=["Reservas"])


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db)):
    return to_out(ReservationService(db).create_reservation(data))


@router.get("/{code}", response_model=ReservationOut)
def get_reservation(code: str, email: str = Query(), db: Session = Depends(get_db)):
    return to_out(ReservationService(db).get_reservation(code, email))


@router.put("/{code}", response_model=ReservationOut)
def update_reservation(code: str, data: ReservationUpdate, db: Session = Depends(get_db)):
    return to_out(ReservationService(db).update_reservation(code, data))


@router.post("/{code}/cancel", response_model=ReservationOut)
def cancel_reservation(code: str, data: OwnerCheck, db: Session = Depends(get_db)):
    return to_out(ReservationService(db).cancel_reservation(code, data.email))


@router.get("/{code}/notifications", response_model=list[NotificationOut])
def reservation_notifications(code: str, email: str = Query(), db: Session = Depends(get_db)):
    reservation = ReservationService(db).get_reservation(code, email)
    return sorted(reservation.notifications, key=lambda n: n.id)
