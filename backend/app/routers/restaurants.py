"""Endpoints de sucursales y disponibilidad (RF-01, RF-02)."""
from datetime import date, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AvailabilityOut, RestaurantOut, TableOut
from ..services.reservations import ReservationService, max_capacity

router = APIRouter(prefix="/api/restaurants", tags=["Sucursales"])


@router.get("", response_model=list[RestaurantOut])
def list_restaurants(db: Session = Depends(get_db)):
    service = ReservationService(db)
    return [RestaurantOut(id=r.id, name=r.name, address=r.address, phone=r.phone,
                          opening_time=r.opening_time, closing_time=r.closing_time,
                          max_capacity=max_capacity(r))
            for r in service.list_restaurants()]


@router.get("/{restaurant_id}/availability", response_model=AvailabilityOut)
def availability(restaurant_id: int, date: date, time: time,
                 party_size: int = Query(ge=1), db: Session = Depends(get_db)):
    table = ReservationService(db).check_availability(restaurant_id, date, time, party_size)
    if table is None:
        return AvailabilityOut(available=False, message="No hay mesas disponibles en ese horario")
    return AvailabilityOut(available=True, table=TableOut.model_validate(table),
                           message=f"Mesa {table.number} disponible ({table.capacity} personas)")
