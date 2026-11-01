"""v1.1 - Programa de recompensas para clientes frecuentes (cambio de requisitos, Fase 4).

Reglas (RF-10 a RF-14):
- Cada reserva COMPLETADA (el cliente asistió) suma POINTS_PER_VISIT puntos, una sola vez.
- El nivel depende de los puntos acumulados históricos (no baja al canjear).
- Con REDEEM_COST puntos de saldo se canjea un cupón de 10 % de descuento.
"""
import secrets
import string
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Customer, NotificationType, Reservation, ReservationStatus,
                      RewardTransaction, RewardType)
from . import reservations as res_module
from .errors import InvalidStateError, NotFoundError, RuleViolationError
from .notifications import NotificationService

POINTS_PER_VISIT = 10
REDEEM_COST = 50
COUPON_BENEFIT = "10 % de descuento en tu próxima visita"
# (nivel, puntos acumulados mínimos) en orden ascendente
LEVELS = [("BRONCE", 0), ("PLATA", 50), ("ORO", 100)]


def level_for(lifetime_points: int) -> str:
    current = LEVELS[0][0]
    for name, minimum in LEVELS:
        if lifetime_points >= minimum:
            current = name
    return current


def next_level(lifetime_points: int) -> tuple[str | None, int]:
    """Devuelve (siguiente nivel, puntos que faltan) o (None, 0) si ya está en el máximo."""
    for name, minimum in LEVELS:
        if lifetime_points < minimum:
            return name, minimum - lifetime_points
    return None, 0


class RewardService:
    def __init__(self, db: Session, notifier: NotificationService | None = None):
        self.db = db
        self.notifier = notifier or NotificationService(db)

    def get_customer(self, email: str) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.email == email.strip().lower()))
        if customer is None:
            raise NotFoundError("Cliente no encontrado")
        return customer

    def complete_reservation(self, code: str) -> tuple[Reservation, RewardTransaction]:
        """Personal del restaurante marca la asistencia; el cliente gana puntos."""
        reservation = self.db.scalar(select(Reservation).where(Reservation.code == code.upper()))
        if reservation is None:
            raise NotFoundError("Reserva no encontrada")
        if reservation.status != ReservationStatus.CONFIRMED:
            raise InvalidStateError("Solo una reserva confirmada puede marcarse como completada")
        if datetime.combine(reservation.date, reservation.start_time) > res_module._now():
            raise InvalidStateError("La reserva aún no ha iniciado; no puede marcarse como completada")

        customer = reservation.customer
        old_level = level_for(customer.lifetime_points)
        reservation.status = ReservationStatus.COMPLETED
        reservation.updated_at = datetime.now()
        customer.points += POINTS_PER_VISIT
        customer.lifetime_points += POINTS_PER_VISIT
        tx = RewardTransaction(customer=customer, reservation_id=reservation.id, type=RewardType.EARN,
                               points=POINTS_PER_VISIT,
                               description=f"Reserva {reservation.code} completada")
        self.db.add(tx)
        self.db.flush()

        new_level = level_for(customer.lifetime_points)
        body = (f"Hola {customer.name}:\nGracias por tu visita. Ganaste {POINTS_PER_VISIT} puntos "
                f"por la reserva {reservation.code}.\nSaldo: {customer.points} puntos. Nivel: {new_level}.")
        if new_level != old_level:
            body += f"\n¡Felicitaciones! Subiste de nivel {old_level} a {new_level}."
        if customer.points >= REDEEM_COST:
            body += f"\nYa puedes canjear {REDEEM_COST} puntos por un cupón de {COUPON_BENEFIT}."
        self.notifier.send(customer, NotificationType.REWARD,
                           f"Ganaste {POINTS_PER_VISIT} puntos - reserva {reservation.code}", body, reservation)
        self.db.commit()
        return reservation, tx

    def summary(self, email: str) -> dict:
        c = self.get_customer(email)
        nxt, missing = next_level(c.lifetime_points)
        txs = sorted(c.reward_transactions, key=lambda t: t.id, reverse=True)
        return {
            "customer_name": c.name, "email": c.email, "points": c.points,
            "lifetime_points": c.lifetime_points, "level": level_for(c.lifetime_points),
            "next_level": nxt, "points_to_next_level": missing,
            "redeem_cost": REDEEM_COST, "can_redeem": c.points >= REDEEM_COST,
            "transactions": txs,
        }

    def redeem(self, email: str) -> RewardTransaction:
        customer = self.get_customer(email)
        if customer.points < REDEEM_COST:
            raise RuleViolationError(
                f"Puntos insuficientes: tienes {customer.points} y se necesitan {REDEEM_COST}")
        coupon = "DESC10-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        customer.points -= REDEEM_COST
        tx = RewardTransaction(customer=customer, type=RewardType.REDEEM, points=-REDEEM_COST,
                               description=f"Canje: cupón de {COUPON_BENEFIT}", coupon_code=coupon)
        self.db.add(tx)
        self.db.flush()
        self.notifier.send(customer, NotificationType.REDEMPTION, f"Tu cupón {coupon}",
                           f"Hola {customer.name}:\nCanjeaste {REDEEM_COST} puntos por un cupón de "
                           f"{COUPON_BENEFIT}.\nCódigo del cupón: {coupon}\nSaldo restante: {customer.points} puntos.")
        self.db.commit()
        return tx
