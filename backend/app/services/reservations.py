"""Reglas de negocio de reservas (capa de servicios)."""
import secrets
import string
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Customer, NotificationType, Reservation, ReservationStatus,
                      Restaurant, Table)
from ..schemas import ReservationCreate, ReservationUpdate
from .errors import (ForbiddenError, InvalidStateError, NoAvailabilityError,
                     NotFoundError, RuleViolationError)
from .notifications import NotificationService

RESERVATION_DURATION = timedelta(hours=2)
MAX_DAYS_AHEAD = 60
CODE_ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime:
    return datetime.now()


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def max_capacity(restaurant: Restaurant) -> int:
    return max((t.capacity for t in restaurant.tables), default=0)


class ReservationService:
    def __init__(self, db: Session, notifier: NotificationService | None = None):
        self.db = db
        self.notifier = notifier or NotificationService(db)

    # ---------- consultas ----------
    def list_restaurants(self) -> list[Restaurant]:
        return list(self.db.scalars(select(Restaurant).order_by(Restaurant.id)))

    def get_restaurant(self, restaurant_id: int) -> Restaurant:
        restaurant = self.db.get(Restaurant, restaurant_id)
        if restaurant is None:
            raise NotFoundError("Sucursal no encontrada")
        return restaurant

    def get_reservation(self, code: str, email: str) -> Reservation:
        reservation = self.db.scalar(select(Reservation).where(Reservation.code == code.upper()))
        if reservation is None:
            raise NotFoundError("Reserva no encontrada")
        if reservation.customer.email != email.strip().lower():
            raise ForbiddenError("El correo no corresponde al titular de la reserva")
        return reservation

    def list_by_customer(self, email: str) -> list[Reservation]:
        stmt = (select(Reservation).join(Customer)
                .where(Customer.email == email.strip().lower())
                .order_by(Reservation.date, Reservation.start_time))
        return list(self.db.scalars(stmt))

    # ---------- reglas ----------
    def validate_slot(self, restaurant: Restaurant, day: date, start: time, party_size: int) -> time:
        """Valida horario, anticipación y capacidad. Devuelve la hora de fin."""
        if start.minute not in (0, 30) or start.second != 0:
            raise RuleViolationError("Las reservas se realizan en horas exactas o medias horas (:00 o :30)")
        start_dt = datetime.combine(day, start)
        end_dt = start_dt + RESERVATION_DURATION
        now = _now()
        if start_dt <= now:
            raise RuleViolationError("La fecha y hora de la reserva deben ser futuras")
        if day > now.date() + timedelta(days=MAX_DAYS_AHEAD):
            raise RuleViolationError(f"Solo se puede reservar con hasta {MAX_DAYS_AHEAD} días de anticipación")
        if start < restaurant.opening_time or end_dt > datetime.combine(day, restaurant.closing_time):
            raise RuleViolationError(
                f"Fuera de horario: la reserva (2 h) debe estar entre "
                f"{restaurant.opening_time:%H:%M} y {restaurant.closing_time:%H:%M}")
        cap = max_capacity(restaurant)
        if party_size > cap:
            raise RuleViolationError(f"El número máximo de personas en esta sucursal es {cap}")
        return end_dt.time()

    def find_free_table(self, restaurant: Restaurant, day: date, start: time, end: time,
                        party_size: int, exclude_reservation_id: int | None = None) -> Table | None:
        """Mesa más pequeña con capacidad suficiente y sin reservas solapadas."""
        busy_stmt = select(Reservation.table_id).where(
            Reservation.restaurant_id == restaurant.id,
            Reservation.date == day,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.start_time < end,
            Reservation.end_time > start,
        )
        if exclude_reservation_id is not None:
            busy_stmt = busy_stmt.where(Reservation.id != exclude_reservation_id)
        busy = set(self.db.scalars(busy_stmt))
        candidates = sorted((t for t in restaurant.tables if t.capacity >= party_size),
                            key=lambda t: (t.capacity, t.number))
        return next((t for t in candidates if t.id not in busy), None)

    def check_availability(self, restaurant_id: int, day: date, start: time, party_size: int) -> Table | None:
        restaurant = self.get_restaurant(restaurant_id)
        end = self.validate_slot(restaurant, day, start, party_size)
        return self.find_free_table(restaurant, day, start, end, party_size)

    # ---------- operaciones ----------
    def _get_or_create_customer(self, name: str, email: str, phone: str) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.email == email))
        if customer is None:
            customer = Customer(name=name, email=email, phone=phone)
            self.db.add(customer)
        else:
            customer.name, customer.phone = name, phone
        self.db.flush()
        return customer

    def _unique_code(self) -> str:
        while True:
            code = generate_code()
            if self.db.scalar(select(Reservation.id).where(Reservation.code == code)) is None:
                return code

    def create_reservation(self, data: ReservationCreate) -> Reservation:
        restaurant = self.get_restaurant(data.restaurant_id)
        end = self.validate_slot(restaurant, data.date, data.time, data.party_size)
        table = self.find_free_table(restaurant, data.date, data.time, end, data.party_size)
        if table is None:
            raise NoAvailabilityError("No hay mesas disponibles para ese horario y número de personas")
        customer = self._get_or_create_customer(data.name, data.email, data.phone)
        reservation = Reservation(
            code=self._unique_code(), customer=customer, restaurant=restaurant, table=table,
            date=data.date, start_time=data.time, end_time=end, party_size=data.party_size,
            notes=data.notes, status=ReservationStatus.CONFIRMED,
        )
        self.db.add(reservation)
        self.db.flush()
        self.notifier.notify(reservation, NotificationType.CONFIRMATION)
        self.db.commit()
        return reservation

    def _ensure_modifiable(self, reservation: Reservation) -> None:
        if reservation.status != ReservationStatus.CONFIRMED:
            raise InvalidStateError("Solo se pueden modificar o cancelar reservas confirmadas")
        if datetime.combine(reservation.date, reservation.start_time) <= _now():
            raise InvalidStateError("La reserva ya inició o pasó; no se puede cambiar")

    def update_reservation(self, code: str, data: ReservationUpdate) -> Reservation:
        reservation = self.get_reservation(code, data.email)
        self._ensure_modifiable(reservation)
        restaurant = self.get_restaurant(data.restaurant_id or reservation.restaurant_id)
        day = data.date or reservation.date
        start = data.time or reservation.start_time
        party = data.party_size or reservation.party_size
        end = self.validate_slot(restaurant, day, start, party)
        table = self.find_free_table(restaurant, day, start, end, party, exclude_reservation_id=reservation.id)
        if table is None:
            raise NoAvailabilityError("No hay mesas disponibles para el nuevo horario")
        reservation.restaurant, reservation.table = restaurant, table
        reservation.date, reservation.start_time, reservation.end_time = day, start, end
        reservation.party_size = party
        if data.notes is not None:
            reservation.notes = data.notes
        reservation.updated_at = datetime.now()
        self.db.flush()
        self.notifier.notify(reservation, NotificationType.MODIFICATION)
        self.db.commit()
        return reservation

    def cancel_reservation(self, code: str, email: str) -> Reservation:
        reservation = self.get_reservation(code, email)
        self._ensure_modifiable(reservation)
        reservation.status = ReservationStatus.CANCELLED
        reservation.updated_at = datetime.now()
        self.db.flush()
        self.notifier.notify(reservation, NotificationType.CANCELLATION)
        self.db.commit()
        return reservation
