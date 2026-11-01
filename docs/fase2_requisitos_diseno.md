# Fase 2 — Requisitos y diseño de software

**Proyecto:** ReservaYa — Sistema de reservas en línea para una cadena de restaurantes
**Versión del documento:** 1.0 (línea base de requisitos)

| Versión ERS | Fecha | Descripción |
|---|---|---|
| 1.0 | 14/10/2026 | Línea base (este documento) |
| 1.1 | 26/10/2026 | Programa de recompensas (RF-10 a RF-14): ver `fase4_mantenimiento.md`, sección 4.1.3 |

---

## 2.1 Requisitos de software

### 2.1.1 Acta de reunión con el cliente (SIMULADA)

> **Nota:** esta reunión es **simulada**. El rol de "cliente" lo asume el gerente de operaciones ficticio de la cadena "Sabores del Sur". Las respuestas se redactaron para representar un escenario realista y sirven como base de la especificación.

| Campo | Detalle |
|---|---|
| Fecha | 12/10/2026 (simulada) |
| Lugar | Laboratorio EPIS – UNSA (virtual) |
| Cliente | Gerente de operaciones de la cadena "Sabores del Sur" (rol simulado) |
| Equipo | Integrantes del grupo de laboratorio |
| Objetivo | Recolectar requisitos del sistema de reservas en línea |

| N.º | Pregunta del equipo | Respuesta del cliente |
|---|---|---|
| 1 | ¿Cuántas sucursales tiene la cadena y cómo se identifican? | Tres sucursales en Arequipa (Centro, Cayma y Yanahuara). Cada una con nombre, dirección, teléfono y horario. |
| 2 | ¿Cuál es el horario de atención? | De 12:00 a 23:00 todos los días. No se aceptan reservas que terminen después del cierre. |
| 3 | ¿Cuánto dura una reserva? | Se bloquea la mesa **2 horas** desde la hora reservada. |
| 4 | ¿Qué datos debe ingresar el cliente? | Nombre, correo electrónico, teléfono, sucursal, fecha, hora, número de personas y comentarios opcionales (alergias, cumpleaños, etc.). |
| 5 | ¿El cliente elige la mesa? | No. El sistema asigna automáticamente la **mesa más pequeña disponible** que alcance para el grupo, para aprovechar el salón. |
| 6 | ¿Con cuánta anticipación se puede reservar? | Desde hoy (solo horas futuras) hasta **60 días** antes. |
| 7 | ¿Se necesita cuenta de usuario? | No en esta versión. El cliente se identifica con su correo y el **código de reserva** que se le envía. |
| 8 | ¿Qué puede cambiar el cliente en una reserva? | Fecha, hora, número de personas y comentarios. La sucursal también, si hay disponibilidad. |
| 9 | ¿Hasta cuándo se puede cancelar? | Mientras la reserva esté confirmada y no haya pasado su hora de inicio. |
| 10 | ¿Qué notificaciones se esperan? | Confirmación al reservar, aviso al modificar y aviso al cancelar, con el código y los datos de la reserva. Por ahora basta con **simular** el envío (registro), luego se conectará el correo. |
| 11 | ¿Cuál es el tamaño máximo de grupo? | El de la mesa más grande de la sucursal (8 personas). Grupos mayores se atienden por teléfono. |

**Acuerdos:** (1) se trabajará con un modelo iterativo, mostrando avances al cliente; (2) las notificaciones serán simuladas en esta versión; (3) el cliente validará la ERS antes de la construcción.

### 2.1.2 Especificación de Requisitos de Software (ERS) — estilo IEEE 830 / ISO/IEC/IEEE 29148

#### 1. Introducción

- **Propósito:** describir los requisitos del sistema ReservaYa para guiar su diseño, construcción y pruebas.
- **Alcance:** aplicación web que permite a clientes de la cadena reservar, consultar, modificar y cancelar reservas de mesas, y recibir notificaciones de cada operación.
- **Definiciones:** *Reserva*: bloqueo de una mesa en una sucursal para una fecha y hora; *Código de reserva*: identificador alfanumérico de 8 caracteres entregado al cliente; *Sucursal*: local de la cadena.
- **Referencias:** SWEBOK v3.0 (Bourque y Fairley, 2014); IEEE Std 830-1998; ISO/IEC/IEEE 29148:2018.

#### 2. Descripción general

- **Perspectiva del producto:** sistema nuevo, independiente, con API REST y cliente web.
- **Usuarios:** *Cliente* (reserva y gestiona sus reservas); *Sistema de notificaciones* (actor secundario).
- **Supuestos:** el cliente dispone de correo válido; el horario es el mismo todos los días.

#### 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RF-01 | El sistema debe listar las sucursales con nombre, dirección, teléfono y horario. | Alta |
| RF-02 | El sistema debe permitir consultar la disponibilidad de mesa para una sucursal, fecha, hora y número de personas. | Alta |
| RF-03 | El sistema debe permitir crear una reserva con los datos del cliente, sucursal, fecha, hora, número de personas y comentarios, asignando automáticamente la mesa más pequeña disponible con capacidad suficiente y generando un código único. | Alta |
| RF-04 | El sistema debe permitir consultar una reserva por su código y listar las reservas de un cliente a partir de su correo. | Alta |
| RF-05 | El sistema debe permitir modificar fecha, hora, sucursal, número de personas y comentarios de una reserva confirmada, revalidando la disponibilidad. | Alta |
| RF-06 | El sistema debe permitir cancelar una reserva confirmada cuya hora de inicio no haya pasado. | Alta |
| RF-07 | El sistema debe enviar una notificación de **confirmación** al cliente al crear una reserva. | Alta |
| RF-08 | El sistema debe enviar una notificación al **modificar** y al **cancelar** una reserva. | Media |
| RF-09 | El sistema debe permitir consultar el historial de notificaciones de una reserva. | Baja |

#### 4. Requisitos no funcionales

| ID | Tipo | Requisito |
|---|---|---|
| RNF-01 | Usabilidad | Una reserva debe completarse en una sola pantalla; la interfaz debe adaptarse a móviles (responsive). |
| RNF-02 | Rendimiento | Las operaciones de la API deben responder en menos de 1 segundo con la base de datos de prueba. |
| RNF-03 | Integridad | No deben existir dos reservas confirmadas que se solapen en la misma mesa. |
| RNF-04 | Seguridad | Toda modificación o cancelación exige el código de reserva **y** el correo del titular; se validan formatos de correo y teléfono. |
| RNF-05 | Mantenibilidad | Arquitectura en capas (presentación, API, servicios, datos) y pruebas automatizadas de la lógica de negocio. |
| RNF-06 | Portabilidad | El sistema debe ejecutarse en Windows, Linux o macOS con Python 3.10 o superior. |
| RNF-07 | Documentación | La API debe exponer su documentación OpenAPI en `/docs`. |

#### 5. Restricciones

- **RS-01:** Tecnología: Python + FastAPI, SQLite (SQLAlchemy), frontend HTML/CSS/JS sin frameworks pesados.
- **RS-02:** Horario de atención 12:00–23:00; la reserva (2 h) debe terminar como máximo a la hora de cierre.
- **RS-03:** Reservas solo en fechas/horas futuras y con un máximo de 60 días de anticipación.
- **RS-04:** Número de personas entre 1 y la capacidad de la mesa más grande de la sucursal.
- **RS-05:** Notificaciones simuladas (registro en base de datos y archivo de log); sin envío real por correo en esta versión.
- **RS-06:** Proyecto académico con un plazo de 4 semanas (una parte por semana).

#### 6. Casos de uso

| ID | Caso de uso | Actor | Flujo principal | RF |
|---|---|---|---|---|
| CU-01 | Consultar sucursales | Cliente | El cliente abre la aplicación y ve las sucursales y sus horarios. | RF-01 |
| CU-02 | Consultar disponibilidad | Cliente | Elige sucursal, fecha, hora y personas; el sistema indica si hay mesa. | RF-02 |
| CU-03 | Reservar mesa | Cliente | Ingresa sus datos y los de la reserva; el sistema valida, asigna mesa, guarda y notifica (incluye CU-07). | RF-03, RF-07 |
| CU-04 | Consultar mis reservas | Cliente | Ingresa su correo y ve la lista de sus reservas. | RF-04 |
| CU-05 | Modificar reserva | Cliente | Selecciona una reserva, cambia datos; el sistema revalida, actualiza y notifica. | RF-05, RF-08 |
| CU-06 | Cancelar reserva | Cliente | Selecciona una reserva y confirma la cancelación; el sistema libera la mesa y notifica. | RF-06, RF-08 |
| CU-07 | Enviar notificación | Sistema | Registra y "envía" el mensaje al correo del cliente. | RF-07, RF-08, RF-09 |

**Flujos alternativos relevantes (CU-03/CU-05):** (a) no hay mesa disponible → mensaje "No hay mesas disponibles" (HTTP 409); (b) fecha/hora fuera de horario o pasada → error de validación (HTTP 422); (c) número de personas mayor a la capacidad máxima → error (HTTP 422).

Diagrama: `docs/diagramas/casos_uso.png`.

#### 7. Criterios de aceptación

| ID | Requisito | Criterio de aceptación (Dado / Cuando / Entonces) |
|---|---|---|
| CA-01 | RF-01 | Dado que existen sucursales registradas, cuando se consulta `/api/restaurants`, entonces se listan las 3 sucursales con su horario. |
| CA-02 | RF-02 | Dada una mesa libre, cuando se consulta disponibilidad, entonces la respuesta indica `available=true` y la mesa asignable. |
| CA-03 | RF-03 | Dados datos válidos, cuando se crea la reserva, entonces se obtiene HTTP 201, un código de 8 caracteres, estado CONFIRMED y la mesa más pequeña que alcanza. |
| CA-04 | RF-03, RNF-03 | Dadas todas las mesas adecuadas ocupadas en ese horario, cuando se intenta reservar, entonces se obtiene HTTP 409 y no se crea la reserva. |
| CA-05 | RF-04 | Dado un correo con reservas, cuando se consultan sus reservas, entonces se listan solo las de ese correo. |
| CA-06 | RF-05 | Dada una reserva confirmada, cuando se cambia la hora a un horario libre, entonces se actualiza y se registra una notificación de modificación. |
| CA-07 | RF-06 | Dada una reserva confirmada, cuando se cancela, entonces su estado es CANCELLED, la mesa queda libre y se registra una notificación de cancelación. |
| CA-08 | RF-07 | Dada una reserva creada, entonces existe una notificación de tipo CONFIRMATION dirigida al correo del cliente. |
| CA-09 | RNF-04 | Dado un correo que no es el del titular, cuando se intenta modificar o cancelar, entonces se obtiene HTTP 403. |

---

## 2.2 Diseño de software

### 2.2.1 Arquitectura del sistema

Arquitectura **cliente-servidor en capas**:

| Capa | Componente | Responsabilidad |
|---|---|---|
| Presentación | Frontend web (`frontend/`: HTML, CSS, JS) | Formularios de reserva, consulta, modificación y cancelación; consume la API con `fetch`. |
| API | Routers FastAPI (`app/routers/`) | Endpoints REST, validación de entrada con Pydantic (`app/schemas.py`), códigos HTTP. |
| Servicios (negocio) | `app/services/` | Reglas de negocio: horario, anticipación, disponibilidad, no solapamiento, asignación de mesa, notificaciones. |
| Datos | SQLAlchemy + SQLite (`app/models.py`, `app/database.py`) | Persistencia de sucursales, mesas, clientes, reservas y notificaciones. |
| Infraestructura | Notificador simulado | Registra cada notificación en BD y en `notifications.log`. |

Diagrama de componentes: `docs/diagramas/arquitectura.png`.

### 2.2.2 Modelo de datos

| Entidad | Atributos principales | Relaciones |
|---|---|---|
| Restaurant (sucursal) | id, name, address, phone, opening_time, closing_time | 1..* Table, 0..* Reservation |
| Table (mesa) | id, restaurant_id, number, capacity, location | pertenece a 1 Restaurant |
| Customer (cliente) | id, name, email (único), phone, created_at | 0..* Reservation, 0..* Notification |
| Reservation (reserva) | id, code (único), customer_id, restaurant_id, table_id, date, start_time, end_time, party_size, status, notes, created_at, updated_at | pertenece a Customer, Restaurant y Table; 0..* Notification |
| Notification (notificación) | id, reservation_id, customer_id, type, channel, recipient, subject, message, status, sent_at | pertenece a Reservation y Customer |

Enumeraciones: `ReservationStatus = {CONFIRMED, CANCELLED}`; `NotificationType = {CONFIRMATION, MODIFICATION, CANCELLATION}`.

### 2.2.3 Diagrama de clases UML

Fuente: `docs/diagramas/clases.puml` — Imagen: `docs/diagramas/clases.png`.

Incluye las entidades del modelo de datos y las clases de servicio `ReservationService` y `NotificationService`, con sus dependencias.

### 2.2.4 Diagrama de secuencia UML — "Crear reserva y notificar"

Fuente: `docs/diagramas/secuencia_crear_reserva.puml` — Imagen: `docs/diagramas/secuencia_crear_reserva.png`.

Flujo: el cliente envía el formulario → el frontend hace `POST /api/reservations` → el router valida el esquema → `ReservationService` valida horario/anticipación, obtiene o crea el cliente, busca la mesa disponible más pequeña sin solapamiento, guarda la reserva → `NotificationService` registra la notificación de confirmación (BD + log) → se responde 201 con el código.

### 2.2.5 Diseño de la API REST

| Método | Ruta | Descripción | RF |
|---|---|---|---|
| GET | `/api/restaurants` | Lista sucursales | RF-01 |
| GET | `/api/restaurants/{id}/availability?date=&time=&party_size=` | Consulta disponibilidad | RF-02 |
| POST | `/api/reservations` | Crea reserva | RF-03, RF-07 |
| GET | `/api/reservations/{code}?email=` | Consulta una reserva | RF-04 |
| GET | `/api/customers/{email}/reservations` | Reservas de un cliente | RF-04 |
| PUT | `/api/reservations/{code}` | Modifica reserva (requiere email) | RF-05, RF-08 |
| POST | `/api/reservations/{code}/cancel` | Cancela reserva (requiere email) | RF-06, RF-08 |
| GET | `/api/reservations/{code}/notifications?email=` | Historial de notificaciones | RF-09 |

---

## Resumen para el informe

- Se simuló la reunión con el cliente (gerente de "Sabores del Sur"): acta con 11 preguntas/respuestas y 3 acuerdos; marcada explícitamente como **simulada**.
- ERS en estilo IEEE 830 / ISO/IEC/IEEE 29148: **9 requisitos funcionales (RF-01 a RF-09)**, **7 no funcionales (RNF-01 a RNF-07)** y **6 restricciones (RS-01 a RS-06)**.
- Reglas de negocio clave: horario 12:00–23:00, duración fija de 2 h, anticipación máxima de 60 días, asignación automática de la mesa más pequeña disponible, sin solapamientos.
- 7 casos de uso (CU-01 a CU-07) con diagrama UML de casos de uso y 9 criterios de aceptación (CA-01 a CA-09) en formato Dado/Cuando/Entonces.
- Arquitectura cliente-servidor en 4 capas: presentación (HTML/CSS/JS), API (FastAPI), servicios (reglas de negocio) y datos (SQLAlchemy + SQLite).
- Modelo de datos con 5 entidades: Restaurant, Table, Customer, Reservation, Notification.
- Diagramas UML entregados en PlantUML (`.puml`) y PNG: casos de uso, componentes/arquitectura, clases y secuencia "crear reserva y notificar".
- Diseño de la API REST con 8 endpoints trazados a los RF.
