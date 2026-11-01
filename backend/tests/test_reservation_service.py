"""Pruebas unitarias de la capa de servicios (reglas de negocio)."""
from datetime import date, time, timedelta

import pytest

from app.models import NotificationType, ReservationStatus
from app.schemas import ReservationUpdate
from app.services import notifications
from app.services.errors import (ForbiddenError, InvalidStateError, NoAvailabilityError,
                                 NotFoundError, RuleViolationError)
from app.services.reservations import ReservationService


@pytest.fixture()
def service(db):
    return ReservationService(db)


# ---------- RF-01 / RF-02 ----------
def test_tp01_lista_tres_sucursales(service):
    restaurants = service.list_restaurants()
    assert len(restaurants) == 3
    assert all(len(r.tables) == 6 for r in restaurants)


def test_tp02_disponibilidad_asigna_mesa_mas_pequena(service, tomorrow):
    table = service.check_availability(1, tomorrow, time(19, 0), 3)
    assert table is not None and table.capacity == 4 and table.number == 3


# ---------- RF-03 / RF-07 ----------
def test_tp03_crear_reserva_valida(service, make_data):
    r = service.create_reservation(make_data(party_size=3))
    assert len(r.code) == 8 and r.code.isalnum()
    assert r.status == ReservationStatus.CONFIRMED
    assert r.end_time == time(15, 0)
    assert r.table.capacity == 4


def test_tp04_crear_reserva_genera_notificacion_confirmacion(service, make_data):
    r = service.create_reservation(make_data())
    assert len(r.notifications) == 1
    n = r.notifications[0]
    assert n.type == NotificationType.CONFIRMATION
    assert n.recipient == "ana@example.com"
    assert r.code in n.subject and r.code in n.message
    with open(notifications.LOG_PATH, encoding="utf-8") as fh:
        assert f"CONFIRMATION -> ana@example.com" in fh.read()


# ---------- RNF-03: no solapamiento ----------
def test_tp05_sin_mesas_disponibles_lanza_409(service, make_data):
    for i in range(6):  # 6 mesas en la sucursal
        service.create_reservation(make_data(email=f"c{i}@example.com"))
    with pytest.raises(NoAvailabilityError):
        service.create_reservation(make_data(email="otro@example.com"))


def test_tp06_misma_mesa_en_horarios_no_solapados(service, make_data):
    r1 = service.create_reservation(make_data(time=time(13, 0)))
    r2 = service.create_reservation(make_data(email="b@example.com", time=time(15, 0)))
    assert r1.table_id == r2.table_id


def test_tp07_horario_solapado_usa_otra_mesa(service, make_data):
    r1 = service.create_reservation(make_data(time=time(13, 0)))
    r2 = service.create_reservation(make_data(email="b@example.com", time=time(14, 0)))
    assert r1.table_id != r2.table_id


# ---------- Validaciones (RS-02, RS-03, RS-04) ----------
def test_tp08_fecha_pasada_rechazada(service, make_data):
    with pytest.raises(RuleViolationError):
        service.create_reservation(make_data(date=date.today() - timedelta(days=1)))


def test_tp09_mas_de_60_dias_rechazada(service, make_data):
    with pytest.raises(RuleViolationError):
        service.create_reservation(make_data(date=date.today() + timedelta(days=61)))


@pytest.mark.parametrize("hour", [time(11, 0), time(21, 30), time(22, 0)])
def test_tp10_fuera_de_horario_rechazada(service, make_data, hour):
    with pytest.raises(RuleViolationError):
        service.create_reservation(make_data(time=hour))


def test_tp11_excede_capacidad_maxima(service, make_data):
    with pytest.raises(RuleViolationError):
        service.create_reservation(make_data(party_size=9))


def test_tp12_minutos_no_permitidos(service, make_data):
    with pytest.raises(RuleViolationError):
        service.create_reservation(make_data(time=time(13, 15)))


# ---------- RF-04 ----------
def test_tp13_lista_solo_reservas_del_cliente(service, make_data):
    service.create_reservation(make_data())
    service.create_reservation(make_data(time=time(18, 0)))
    service.create_reservation(make_data(email="otro@example.com"))
    result = service.list_by_customer("ANA@example.com")
    assert len(result) == 2
    assert all(r.customer.email == "ana@example.com" for r in result)


# ---------- RF-05 / RF-08 ----------
def test_tp14_modificar_hora_y_notificar(service, make_data):
    r = service.create_reservation(make_data())
    upd = service.update_reservation(r.code, ReservationUpdate(email="ana@example.com", time=time(20, 0)))
    assert upd.start_time == time(20, 0) and upd.end_time == time(22, 0)
    assert [n.type for n in upd.notifications] == [NotificationType.CONFIRMATION, NotificationType.MODIFICATION]


def test_tp15_modificar_a_horario_ocupado_falla_sin_cambios(service, make_data):
    # ocupar todas las mesas a las 19:00
    for i in range(6):
        service.create_reservation(make_data(email=f"c{i}@example.com", time=time(19, 0)))
    r = service.create_reservation(make_data(time=time(13, 0)))
    with pytest.raises(NoAvailabilityError):
        service.update_reservation(r.code, ReservationUpdate(email="ana@example.com", time=time(19, 0)))
    service.db.rollback()
    assert service.get_reservation(r.code, "ana@example.com").start_time == time(13, 0)


def test_tp16_modificar_sin_cambiar_horario_no_choca_consigo_misma(service, make_data):
    r = service.create_reservation(make_data(party_size=2))
    upd = service.update_reservation(r.code, ReservationUpdate(email="ana@example.com", notes="Cumpleaños"))
    assert upd.table_id == r.table_id and upd.notes == "Cumpleaños"


# ---------- RF-06 / RF-08 ----------
def test_tp17_cancelar_libera_mesa_y_notifica(service, make_data):
    for i in range(6):
        service.create_reservation(make_data(email=f"c{i}@example.com"))
    victim = service.list_by_customer("c0@example.com")[0]
    cancelled = service.cancel_reservation(victim.code, "c0@example.com")
    assert cancelled.status == ReservationStatus.CANCELLED
    assert cancelled.notifications[-1].type == NotificationType.CANCELLATION
    nueva = service.create_reservation(make_data(email="nuevo@example.com"))
    assert nueva.table_id == victim.table_id


def test_tp18_no_se_cancela_dos_veces(service, make_data):
    r = service.create_reservation(make_data())
    service.cancel_reservation(r.code, "ana@example.com")
    with pytest.raises(InvalidStateError):
        service.cancel_reservation(r.code, "ana@example.com")


# ---------- RNF-04 ----------
def test_tp19_correo_distinto_al_titular_prohibido(service, make_data):
    r = service.create_reservation(make_data())
    with pytest.raises(ForbiddenError):
        service.cancel_reservation(r.code, "intruso@example.com")
    with pytest.raises(ForbiddenError):
        service.update_reservation(r.code, ReservationUpdate(email="intruso@example.com", party_size=4))


def test_tp20_codigo_inexistente(service):
    with pytest.raises(NotFoundError):
        service.get_reservation("ZZZZZZZZ", "ana@example.com")
