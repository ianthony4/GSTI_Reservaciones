"""v1.1 - Pruebas del programa de recompensas (cambio de requisitos de la Fase 4)."""
from datetime import datetime, time, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.models import Notification, NotificationType, ReservationStatus, RewardType
from app.schemas import ReservationUpdate
from app.services import reservations as res_module
from app.services.errors import InvalidStateError, RuleViolationError
from app.services.reservations import ReservationService
from app.services.rewards import RewardService, level_for, next_level

SLOTS = [time(12, 0), time(14, 0), time(16, 0), time(18, 0), time(20, 0)]


@pytest.fixture()
def rs(db):
    return ReservationService(db)


@pytest.fixture()
def rw(db):
    return RewardService(db)


@pytest.fixture()
def time_travel(monkeypatch, tomorrow):
    """Simula el paso del tiempo: tras reservar, 'ahora' pasa a ser dentro de 30 días."""
    def _travel():
        monkeypatch.setattr(res_module, "_now", lambda: datetime.combine(tomorrow + timedelta(days=30), time(23, 59)))
    return _travel


def book(rs, make_data, n, email="ana@example.com", travel=None):
    """Crea n reservas futuras del cliente y, si se indica, avanza el reloj."""
    out = []
    for i in range(n):
        d = make_data(email=email, time=SLOTS[i % 5])
        d.date = d.date + timedelta(days=i // 5)
        out.append(rs.create_reservation(d))
    if travel:
        travel()
    return out


def test_tp28_niveles_por_puntos_acumulados():
    assert [level_for(p) for p in (0, 49, 50, 99, 100, 500)] == ["BRONCE", "BRONCE", "PLATA", "PLATA", "ORO", "ORO"]
    assert next_level(0) == ("PLATA", 50)
    assert next_level(60) == ("ORO", 40)
    assert next_level(100) == (None, 0)


def test_tp29_completar_reserva_otorga_10_puntos_y_notifica(rs, rw, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    reservation, tx = rw.complete_reservation(r.code)
    assert reservation.status == ReservationStatus.COMPLETED
    assert tx.type == RewardType.EARN and tx.points == 10
    assert reservation.customer.points == 10 and reservation.customer.lifetime_points == 10
    assert reservation.notifications[-1].type == NotificationType.REWARD


def test_tp30_no_se_completa_antes_de_iniciar(rs, rw, make_data):
    r = book(rs, make_data, 1)[0]
    with pytest.raises(InvalidStateError):
        rw.complete_reservation(r.code)


def test_tp31_no_se_otorgan_puntos_dos_veces(rs, rw, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    rw.complete_reservation(r.code)
    with pytest.raises(InvalidStateError):
        rw.complete_reservation(r.code)
    assert rw.summary("ana@example.com")["points"] == 10


def test_tp32_reserva_cancelada_no_suma_puntos(rs, rw, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    r.status = ReservationStatus.CANCELLED
    rs.db.commit()
    with pytest.raises(InvalidStateError):
        rw.complete_reservation(r.code)
    assert r.customer.points == 0


def test_tp33_sube_de_nivel_plata_y_oro(rs, rw, make_data, time_travel):
    rsv = book(rs, make_data, 10, travel=time_travel)
    for r in rsv[:5]:
        rw.complete_reservation(r.code)
    s = rw.summary("ana@example.com")
    assert s["level"] == "PLATA" and s["points"] == 50 and s["can_redeem"] is True
    assert "Subiste de nivel BRONCE a PLATA" in rsv[4].notifications[-1].message
    for r in rsv[5:]:
        rw.complete_reservation(r.code)
    assert rw.summary("ana@example.com")["level"] == "ORO"


def test_tp34_canje_con_puntos_insuficientes(rs, rw, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    rw.complete_reservation(r.code)
    with pytest.raises(RuleViolationError):
        rw.redeem("ana@example.com")
    assert rw.summary("ana@example.com")["points"] == 10


def test_tp35_canje_genera_cupon_y_no_baja_nivel(rs, rw, make_data, time_travel):
    for r in book(rs, make_data, 5, travel=time_travel):
        rw.complete_reservation(r.code)
    tx = rw.redeem("ana@example.com")
    assert tx.type == RewardType.REDEEM and tx.points == -50 and tx.coupon_code.startswith("DESC10-")
    s = rw.summary("ana@example.com")
    assert s["points"] == 0 and s["lifetime_points"] == 50 and s["level"] == "PLATA"
    last = tx.customer.reward_transactions[-1]
    assert last.coupon_code == tx.coupon_code
    notif = rs.db.query(Notification).filter_by(type=NotificationType.REDEMPTION).one()
    assert notif.reservation_id is None and tx.coupon_code in notif.message


def test_tp36_reserva_completada_no_se_modifica_ni_cancela(rs, rw, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    rw.complete_reservation(r.code)
    with pytest.raises(InvalidStateError):
        rs.cancel_reservation(r.code, "ana@example.com")
    with pytest.raises(InvalidStateError):
        rs.update_reservation(r.code, ReservationUpdate(email="ana@example.com", party_size=3))


# ---------- API ----------
def test_tp37_api_completar_requiere_clave_de_personal(client, rs, make_data, time_travel):
    r = book(rs, make_data, 1, travel=time_travel)[0]
    assert client.post(f"/api/reservations/{r.code}/complete").status_code == 401
    assert client.post(f"/api/reservations/{r.code}/complete", headers={"X-Staff-Key": "x"}).status_code == 401
    res = client.post(f"/api/reservations/{r.code}/complete", headers={"X-Staff-Key": "staff-demo-key"})
    assert res.status_code == 200
    assert res.json() == {"code": r.code, "status": "COMPLETED", "points_earned": 10,
                          "customer_points": 10, "customer_level": "BRONCE"}


def test_tp38_api_resumen_y_canje(client, rs, make_data, time_travel):
    rsv = book(rs, make_data, 5, travel=time_travel)
    assert client.post("/api/customers/ana@example.com/rewards/redeem").status_code == 422
    for r in rsv:
        client.post(f"/api/reservations/{r.code}/complete", headers={"X-Staff-Key": "staff-demo-key"})
    s = client.get("/api/customers/ana@example.com/rewards").json()
    assert s["level"] == "PLATA" and s["points"] == 50 and s["next_level"] == "ORO" and s["points_to_next_level"] == 50
    red = client.post("/api/customers/ana@example.com/rewards/redeem")
    assert red.status_code == 200 and red.json()["remaining_points"] == 0
    assert client.get("/api/customers/nadie@example.com/rewards").status_code == 404


# ---------- Mantenimiento: migración de datos ----------
def test_tp39_migracion_bd_v1_a_v1_1_conserva_datos(tmp_path):
    from app.migrations import migrate
    engine = create_engine(f"sqlite:///{tmp_path / 'v1.db'}")
    ddl = (Path(__file__).parent / "data" / "schema_v1.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in [s for s in ddl.split(";") if "CREATE" in s]:
            conn.execute(text(stmt))
        conn.execute(text("INSERT INTO restaurants VALUES (1,'R','Dir','1','12:00:00.000000','23:00:00.000000')"))
        conn.execute(text("INSERT INTO tables VALUES (1,1,1,2,'Ventana')"))
        conn.execute(text("INSERT INTO customers VALUES (1,'Ana','ana@example.com','999','2026-10-01 10:00:00')"))
        conn.execute(text("INSERT INTO reservations VALUES (1,'ABCD1234',1,1,1,'2026-10-02','13:00:00.000000',"
                          "'15:00:00.000000',2,'CONFIRMED','','2026-10-01 10:00:00','2026-10-01 10:00:00')"))
        conn.execute(text("INSERT INTO notifications VALUES (1,1,1,'CONFIRMATION','EMAIL','ana@example.com',"
                          "'Asunto','Mensaje','SENT','2026-10-01 10:00:00')"))
    steps = migrate(engine)
    assert any("points" in s for s in steps) and any("notifications" in s for s in steps)
    insp = inspect(engine)
    assert {"points", "lifetime_points"} <= {c["name"] for c in insp.get_columns("customers")}
    assert next(c for c in insp.get_columns("notifications") if c["name"] == "reservation_id")["nullable"]
    assert "reward_transactions" in insp.get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT points FROM customers WHERE id=1")).scalar() == 0
        assert conn.execute(text("SELECT subject FROM notifications WHERE id=1")).scalar() == "Asunto"
        assert conn.execute(text("SELECT code FROM reservations")).scalar() == "ABCD1234"
    assert migrate(engine) == []  # idempotente
    engine.dispose()
