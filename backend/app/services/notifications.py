"""Servicio de notificaciones (simulado: registro en BD y en archivo de log)."""
import os
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Customer, Notification, NotificationType, Reservation

LOG_PATH = os.getenv("RESERVAYA_NOTIF_LOG", "notifications.log")

SUBJECTS = {
    NotificationType.CONFIRMATION: "Confirmación de tu reserva {code}",
    NotificationType.MODIFICATION: "Tu reserva {code} fue modificada",
    NotificationType.CANCELLATION: "Tu reserva {code} fue cancelada",
}

INTROS = {
    NotificationType.CONFIRMATION: "Tu reserva ha sido confirmada.",
    NotificationType.MODIFICATION: "Los datos de tu reserva se actualizaron correctamente.",
    NotificationType.CANCELLATION: "Tu reserva ha sido cancelada. Esperamos verte pronto.",
}


class NotificationService:
    def __init__(self, db: Session, log_path: str | None = None):
        self.db = db
        self.log_path = log_path or LOG_PATH

    def build_message(self, reservation: Reservation, ntype: NotificationType) -> str:
        r = reservation
        return (
            f"Hola {r.customer.name}:\n"
            f"{INTROS[ntype]}\n"
            f"Código: {r.code}\n"
            f"Sucursal: {r.restaurant.name} ({r.restaurant.address})\n"
            f"Fecha: {r.date.strftime('%d/%m/%Y')}  Hora: {r.start_time.strftime('%H:%M')}"
            f"-{r.end_time.strftime('%H:%M')}\n"
            f"Personas: {r.party_size}  Mesa: {r.table.number}"
        )

    def notify(self, reservation: Reservation, ntype: NotificationType) -> Notification:
        return self.send(reservation.customer, ntype,
                         SUBJECTS[ntype].format(code=reservation.code),
                         self.build_message(reservation, ntype), reservation)

    def send(self, customer: Customer, ntype: NotificationType, subject: str, message: str,
             reservation: Reservation | None = None) -> Notification:
        """Registra y "envía" una notificación libre (v1.1: usada por recompensas)."""
        notification = Notification(
            reservation_id=reservation.id if reservation else None,
            customer_id=customer.id,
            type=ntype,
            channel="EMAIL",
            recipient=customer.email,
            subject=subject,
            message=message,
            status="SENT",
            sent_at=datetime.now(),
        )
        self.db.add(notification)
        self.db.flush()
        self._write_log(notification)
        return notification

    def _write_log(self, n: Notification) -> None:
        line = f"[{n.sent_at:%Y-%m-%d %H:%M:%S}] {n.type.value} -> {n.recipient} | {n.subject}\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            # El log es auxiliar: si falla, la notificación sigue registrada en BD.
            pass
