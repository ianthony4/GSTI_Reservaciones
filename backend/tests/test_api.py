"""Pruebas de la API REST con TestClient (integración router + servicio + BD)."""

BASE = {"name": "Luis Quispe", "email": "luis@example.com", "phone": "+51 912345678",
        "restaurant_id": 2, "time": "19:00", "party_size": 4, "notes": "Aniversario"}


def payload(tomorrow, **kw):
    data = dict(BASE, date=tomorrow.isoformat())
    data.update(kw)
    return data


def test_tp21_get_sucursales(client):
    res = client.get("/api/restaurants")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 3 and body[0]["max_capacity"] == 8
    assert body[0]["opening_time"] == "12:00:00"


def test_tp22_post_reserva_valida_201(client, tomorrow):
    res = client.post("/api/reservations", json=payload(tomorrow))
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "CONFIRMED" and len(body["code"]) == 8
    assert body["table_capacity"] == 4 and body["end_time"] == "21:00:00"


def test_tp23_post_datos_invalidos_422(client, tomorrow):
    assert client.post("/api/reservations", json=payload(tomorrow, email="no-es-correo")).status_code == 422
    assert client.post("/api/reservations", json=payload(tomorrow, phone="abc")).status_code == 422
    assert client.post("/api/reservations", json=payload(tomorrow, party_size=0)).status_code == 422
    res = client.post("/api/reservations", json=payload(tomorrow, time="23:00"))
    assert res.status_code == 422 and "horario" in res.json()["detail"]


def test_tp24_flujo_completo_crear_consultar_modificar_cancelar(client, tomorrow):
    code = client.post("/api/reservations", json=payload(tomorrow)).json()["code"]
    q = {"email": "luis@example.com"}
    assert client.get(f"/api/reservations/{code}", params=q).json()["party_size"] == 4
    upd = client.put(f"/api/reservations/{code}", json={"email": "luis@example.com", "party_size": 6, "time": "20:00"})
    assert upd.status_code == 200 and upd.json()["table_capacity"] == 6
    cancel = client.post(f"/api/reservations/{code}/cancel", json=q)
    assert cancel.status_code == 200 and cancel.json()["status"] == "CANCELLED"
    notifs = client.get(f"/api/reservations/{code}/notifications", params=q).json()
    assert [n["type"] for n in notifs] == ["CONFIRMATION", "MODIFICATION", "CANCELLATION"]


def test_tp25_endpoint_disponibilidad(client, tomorrow):
    res = client.get("/api/restaurants/1/availability",
                     params={"date": tomorrow.isoformat(), "time": "13:00", "party_size": 5})
    assert res.status_code == 200
    assert res.json()["available"] is True and res.json()["table"]["capacity"] == 6


def test_tp26_reservas_por_cliente_y_403(client, tomorrow):
    code = client.post("/api/reservations", json=payload(tomorrow)).json()["code"]
    client.post("/api/reservations", json=payload(tomorrow, email="otra@example.com"))
    mine = client.get("/api/customers/luis@example.com/reservations").json()
    assert [r["code"] for r in mine] == [code]
    res = client.post(f"/api/reservations/{code}/cancel", json={"email": "otra@example.com"})
    assert res.status_code == 403


def test_tp27_reserva_inexistente_404_y_conflicto_409(client, tomorrow):
    assert client.get("/api/reservations/NOEXISTE", params={"email": "a@b.com"}).status_code == 404
    for i in range(6):
        client.post("/api/reservations", json=payload(tomorrow, email=f"g{i}@example.com", party_size=2))
    res = client.post("/api/reservations", json=payload(tomorrow, party_size=2))
    assert res.status_code == 409
