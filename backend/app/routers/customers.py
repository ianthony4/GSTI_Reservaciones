"""Endpoints de clientes (RF-04)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ReservationOut
from ..services.reservations import ReservationService
from .common import to_out

router = APIRouter(prefix="/api/customers", tags=["Clientes"])


@router.get("/{email}/reservations", response_model=list[ReservationOut])
def customer_reservations(email: str, db: Session = Depends(get_db)):
    return [to_out(r) for r in ReservationService(db).list_by_customer(email)]
