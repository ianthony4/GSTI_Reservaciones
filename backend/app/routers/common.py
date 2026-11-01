"""Utilidades compartidas por los routers."""
from ..models import Reservation
from ..schemas import ReservationOut


def to_out(r: Reservation) -> ReservationOut:
    return ReservationOut(
        code=r.code, status=r.status, restaurant_id=r.restaurant_id,
        restaurant_name=r.restaurant.name, table_number=r.table.number,
        table_capacity=r.table.capacity, customer_name=r.customer.name,
        customer_email=r.customer.email, date=r.date, start_time=r.start_time,
        end_time=r.end_time, party_size=r.party_size, notes=r.notes,
        created_at=r.created_at, updated_at=r.updated_at,
    )
