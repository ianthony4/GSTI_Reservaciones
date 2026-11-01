# Fase 3 — Construcción y pruebas de software

**Proyecto:** ReservaYa · **Versión del sistema:** 1.0.0

---

## 3.1 Construcción del software

### 3.1.1 Mockups (diseño de interfaces)

Antes de codificar se diseñaron **wireframes de baja fidelidad** en HTML/CSS (carpeta `mockups/`), uno por cada pantalla clave. Capturas en `docs/evidencias/`:

| Mockup | Archivo fuente | Captura | Casos de uso |
|---|---|---|---|
| 1. Reservar mesa | `mockups/01_reservar.html` | `mockup_01_reservar.png` | CU-01, CU-02, CU-03 |
| 2. Confirmación de reserva | `mockups/02_confirmacion.html` | `mockup_02_confirmacion.png` | CU-03, CU-07 |
| 3. Mis reservas / modificar / cancelar | `mockups/03_mis_reservas.html` | `mockup_03_mis_reservas.png` | CU-04, CU-05, CU-06 |

Decisiones de diseño: reserva en **una sola pantalla** (RNF-01); tarjetas de sucursal clicables; el sistema asigna la mesa (el cliente no la elige); la confirmación muestra el **código** de reserva y una vista previa de la notificación enviada; la modificación se hace en un formulario desplegable dentro de la tarjeta de la reserva.

### 3.1.2 Estructura del código

```
backend/
├── app/
│   ├── main.py              # FastAPI: routers, manejo de errores, sirve el frontend
│   ├── database.py          # motor SQLite + sesión SQLAlchemy
│   ├── models.py            # Restaurant, Table, Customer, Reservation, Notification
│   ├── schemas.py           # validación Pydantic (correo, teléfono, rangos)
│   ├── seed.py              # 3 sucursales × 6 mesas (2,2,4,4,6,8)
│   ├── routers/             # restaurants.py, reservations.py, customers.py
│   └── services/
│       ├── reservations.py  # ReservationService: reglas de negocio
│       ├── notifications.py # NotificationService: notificaciones simuladas
│       └── errors.py        # errores de negocio → códigos HTTP
├── tests/                   # conftest.py, test_reservation_service.py, test_api.py
├── requirements.txt
└── pytest.ini
frontend/                    # index.html, styles.css, app.js (fetch a /api)
```

### 3.1.3 Funcionalidades implementadas

| Funcionalidad | Implementación | RF / RNF |
|---|---|---|
| Listar sucursales | `GET /api/restaurants` (incluye capacidad máxima) | RF-01 |
| Consultar disponibilidad | `GET /api/restaurants/{id}/availability` | RF-02 |
| Crear reserva | `POST /api/reservations` → valida, asigna la mesa más pequeña libre, genera código de 8 caracteres | RF-03 |
| Consultar reservas | `GET /api/reservations/{code}?email=` y `GET /api/customers/{email}/reservations` | RF-04 |
| Modificar reserva | `PUT /api/reservations/{code}` (revalida y reasigna mesa excluyendo la propia reserva) | RF-05 |
| Cancelar reserva | `POST /api/reservations/{code}/cancel` (libera la mesa) | RF-06 |
| Notificaciones | `NotificationService.notify()` registra en BD (`notifications`) y en `notifications.log` para CONFIRMATION, MODIFICATION y CANCELLATION | RF-07, RF-08 |
| Historial de notificaciones | `GET /api/reservations/{code}/notifications?email=` | RF-09 |
| Control de titularidad | modificar/cancelar/consultar exige el correo del titular (HTTP 403 si no coincide) | RNF-04 |
| Documentación OpenAPI | `/docs` generado por FastAPI | RNF-07 |

**Reglas de validación implementadas** (`ReservationService.validate_slot` y `find_free_table`):

- Hora de inicio en punto o y media (:00 / :30).
- Fecha y hora futuras; como máximo 60 días de anticipación (RS-03).
- Dentro del horario 12:00–23:00 y fin de la reserva (inicio + 2 h) no posterior al cierre (RS-02).
- Personas ≤ capacidad de la mesa más grande de la sucursal (RS-04).
- **No solapamiento** (RNF-03): una mesa está ocupada si existe una reserva CONFIRMED en la misma fecha con `inicio_existente < fin_nuevo` y `fin_existente > inicio_nuevo`.
- Asignación: mesa con menor capacidad suficiente; desempate por número de mesa.

Mapeo de errores a HTTP: 404 (no encontrado), 403 (correo no titular), 409 (sin mesas o estado inválido), 422 (regla de negocio o formato inválido).

### 3.1.4 Evidencias del sistema funcionando

Capturas tomadas con el servidor real (`uvicorn`) y un navegador Chromium automatizado:

| Captura | Qué muestra |
|---|---|
| `app_01_reservar.png` | Formulario de reserva con sucursal seleccionada y verificación de disponibilidad exitosa |
| `app_02_confirmacion.png` | Confirmación con código, datos de la reserva y notificación enviada |
| `app_03_validacion_error.png` | Error de validación: 9 personas excede la capacidad máxima (8) |
| `app_04_mis_reservas.png` | Lista de reservas del cliente por correo |
| `app_05_modificar_form.png` | Formulario de modificación desplegado |
| `app_06_modificada_cancelada_notificaciones.png` | Reserva modificada (20:00, 5 personas, mesa 5), otra cancelada e historial de notificaciones |
| `app_07_openapi_docs.png` | Documentación automática de la API (`/docs`) |
| `app_08_movil.png` | Vista en móvil (390 px de ancho, RNF-01) |
| `notifications_demo.log` | Log de notificaciones generado durante la demostración (confirmación ×2, modificación, cancelación) |
| `tiempos_respuesta.txt` | Tiempos de respuesta medidos con `curl` (todos < 10 ms; RNF-02 exige < 1 s) |

## 3.2 Pruebas de software

### 3.2.1 Plan de pruebas

- **Objetivo:** verificar que el sistema cumple los RF-01 a RF-09 y los RNF-03/RNF-04, y validar los criterios de aceptación CA-01 a CA-09.
- **Alcance:** capa de servicios (pruebas unitarias) y API REST (pruebas de integración con `fastapi.testclient.TestClient`).
- **Herramientas:** pytest 8, base de datos SQLite **en memoria** independiente por prueba (fixture `db`), log de notificaciones en directorio temporal.
- **Entorno:** Python 3.13, Linux; datos iniciales: 3 sucursales × 6 mesas (capacidades 2, 2, 4, 4, 6, 8).
- **Criterio de salida:** 100 % de los casos ejecutados y aprobados.
- **Fechas de prueba:** relativas al día de ejecución (mañana = hoy + 1) para que las pruebas no caduquen.

### 3.2.2 Casos de prueba

| ID | Funcionalidad | Descripción | Entrada | Resultado esperado | Criterio de aceptación | Resultado obtenido |
|---|---|---|---|---|---|---|
| TP-01 | RF-01 | Listar sucursales | — | 3 sucursales, 6 mesas cada una | CA-01 | PASSED |
| TP-02 | RF-02 | Disponibilidad asigna mesa más pequeña | Sucursal 1, mañana 19:00, 3 pers. | Mesa 3 (cap. 4) | CA-02 | PASSED |
| TP-03 | RF-03 | Crear reserva válida | 3 pers., 13:00 | Código 8 caracteres, CONFIRMED, fin 15:00, mesa cap. 4 | CA-03 | PASSED |
| TP-04 | RF-07 | Notificación de confirmación | Reserva válida | 1 notificación CONFIRMATION al correo del cliente; línea en log | CA-08 | PASSED |
| TP-05 | RNF-03 | Sin mesas disponibles | 7 reservas de 2 pers. a la misma hora | La 7.ª lanza `NoAvailabilityError` (409) | CA-04 | PASSED |
| TP-06 | RNF-03 | Misma mesa sin solapamiento | 13:00 y 15:00 | Ambas en la misma mesa | CA-04 | PASSED |
| TP-07 | RNF-03 | Solapamiento parcial | 13:00 y 14:00 | Mesas distintas | CA-04 | PASSED |
| TP-08 | RS-03 | Fecha pasada | Ayer | Error de regla (422) | — | PASSED |
| TP-09 | RS-03 | Más de 60 días | Hoy + 61 | Error de regla (422) | — | PASSED |
| TP-10 | RS-02 | Fuera de horario (3 variantes) | 11:00, 21:30, 22:00 | Error de regla (422) | — | PASSED (×3) |
| TP-11 | RS-04 | Excede capacidad | 9 personas | Error de regla (422) | — | PASSED |
| TP-12 | Validación | Minutos no permitidos | 13:15 | Error de regla (422) | — | PASSED |
| TP-13 | RF-04 | Reservas por cliente | 2 reservas de Ana + 1 de otro | Solo las 2 de Ana (correo sin distinguir mayúsculas) | CA-05 | PASSED |
| TP-14 | RF-05, RF-08 | Modificar hora | 13:00 → 20:00 | Nuevo horario 20:00–22:00; notificaciones CONFIRMATION + MODIFICATION | CA-06 | PASSED |
| TP-15 | RF-05 | Modificar a horario lleno | 19:00 con 6 mesas ocupadas | 409 y la reserva conserva 13:00 | CA-04 | PASSED |
| TP-16 | RF-05 | Modificar sin cambiar horario | Solo comentarios | Misma mesa; no choca consigo misma | CA-06 | PASSED |
| TP-17 | RF-06, RF-08 | Cancelar libera mesa | Cancelar 1 de 6 reservas | CANCELLED, notificación CANCELLATION, nueva reserva usa esa mesa | CA-07 | PASSED |
| TP-18 | RF-06 | Doble cancelación | Cancelar dos veces | 2.º intento: `InvalidStateError` (409) | — | PASSED |
| TP-19 | RNF-04 | Correo no titular | Correo distinto | `ForbiddenError` (403) al cancelar y modificar | CA-09 | PASSED |
| TP-20 | RF-04 | Código inexistente | `ZZZZZZZZ` | `NotFoundError` (404) | — | PASSED |
| TP-21 | RF-01 (API) | `GET /api/restaurants` | — | 200, 3 sucursales, capacidad máx. 8, apertura 12:00 | CA-01 | PASSED |
| TP-22 | RF-03 (API) | `POST /api/reservations` válido | 4 pers., 19:00 | 201, CONFIRMED, mesa cap. 4, fin 21:00 | CA-03 | PASSED |
| TP-23 | RNF-04 (API) | Datos inválidos | correo, teléfono, 0 personas, 23:00 | 422 en los 4 casos; mensaje con "horario" | — | PASSED |
| TP-24 | RF-03..RF-09 (API) | Flujo completo | crear → consultar → modificar → cancelar | Notificaciones en orden CONFIRMATION, MODIFICATION, CANCELLATION | CA-06, CA-07 | PASSED |
| TP-25 | RF-02 (API) | Endpoint de disponibilidad | 5 personas | `available=true`, mesa cap. 6 | CA-02 | PASSED |
| TP-26 | RF-04, RNF-04 (API) | Reservas por cliente y 403 | 2 clientes | Solo la propia; 403 al cancelar con otro correo | CA-05, CA-09 | PASSED |
| TP-27 | API | 404 y 409 | código inexistente; 7.ª reserva | 404 y 409 | CA-04 | PASSED |

### 3.2.3 Resultados

Salida real guardada en `docs/evidencias/pytest_fase3.txt`:

- **29 pruebas ejecutadas** (27 casos; TP-10 parametrizado en 3 variantes), **29 aprobadas, 0 fallidas**, tiempo ≈ 0.5 s.
- 1 advertencia de deprecación de la librería Starlette/httpx en `TestClient` (no afecta los resultados).
- Todos los criterios de aceptación CA-01 a CA-09 quedan cubiertos por al menos un caso de prueba.

---
