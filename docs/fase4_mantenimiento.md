# Fase 4 — Mantenimiento y revisión del proyecto

**Proyecto:** ReservaYa · **Versión del sistema:** 1.1.0 · **Versión de la ERS:** 1.1

---

## 4.1 Mantenimiento de software

### 4.1.1 Solicitud de cambio (simulada)

> **Nota:** solicitud **simulada**, representando al mismo cliente de la Fase 2.

| Campo | Detalle |
|---|---|
| ID | SC-01 |
| Fecha | 26/10/2026 (simulada) |
| Solicitante | Gerente de operaciones de "Sabores del Sur" |
| Descripción | "Queremos premiar a los clientes frecuentes: que ganen puntos cada vez que vienen, que tengan niveles y que puedan canjear los puntos por un descuento." |
| Prioridad | Media |
| Estado | Aprobada e implementada en v1.1 |

**Análisis del cambio (preguntas y acuerdos):**

| Pregunta | Decisión acordada |
|---|---|
| ¿Cuándo se ganan puntos? | Cuando la reserva se **completa**, es decir, el cliente asistió. Lo marca el personal del restaurante. Reservar sin asistir no da puntos. |
| ¿Cuántos puntos? | **10 puntos** por reserva completada, una sola vez por reserva. |
| ¿Qué niveles hay? | **Bronce** (0–49), **Plata** (50–99) y **Oro** (100 o más), según los puntos **acumulados históricos**. Canjear no baja el nivel. |
| ¿Qué beneficio se obtiene? | Con **50 puntos** de saldo se canjea un **cupón de 10 % de descuento**. |
| ¿Se avisa al cliente? | Sí: notificación al ganar puntos (con aviso de subida de nivel) y al canjear (con el código del cupón). |
| ¿Quién marca la asistencia? | Solo el personal, con una **clave de personal** (`X-Staff-Key`). |

### 4.1.2 Análisis de impacto

| Elemento | Impacto | Cambio realizado |
|---|---|---|
| Requisitos | Nuevos RF-10 a RF-14 y RNF-08; RF-09 ampliado | ERS v1.1 (abajo) |
| Modelo de datos | `Customer` +2 columnas; nuevo `RewardTransaction`; `ReservationStatus` + COMPLETED; `NotificationType` + REWARD, REDEMPTION; `Notification.reservation_id` pasa a opcional | `app/models.py` |
| Base de datos existente | Una BD v1.0 ya tiene datos | Migración automática e idempotente `app/migrations.py` |
| Servicios | Nuevo `RewardService`; `NotificationService.send()` genérico | `app/services/rewards.py`, `notifications.py` |
| API | 3 endpoints nuevos | `app/routers/rewards.py` |
| Frontend | Panel "Programa Clientes Frecuentes" en *Mis reservas*; estado "Completada" | `frontend/` |
| Pruebas | 12 pruebas nuevas + regresión completa de las 29 anteriores | `tests/test_rewards.py` |
| Funcionalidad existente | Sin cambios de comportamiento: crear/modificar/cancelar se mantienen | Verificado por regresión |

### 4.1.3 Documento de requisitos actualizado (ERS v1.1)

#### Historial de cambios de la ERS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| 1.0 | 14/10/2026 | Equipo | Línea base: RF-01 a RF-09, RNF-01 a RNF-07, RS-01 a RS-06 (Fase 2). |
| 1.1 | 26/10/2026 | Equipo | SC-01: programa de recompensas. Se agregan RF-10 a RF-14, RNF-08 y RS-07; se amplía RF-09; nuevo estado COMPLETED. |

#### Requisitos funcionales nuevos

| ID | Requisito | Prioridad | Versión |
|---|---|---|---|
| RF-10 | El personal del restaurante debe poder marcar como **completada** una reserva confirmada cuya hora de inicio ya pasó. | Alta | 1.1 |
| RF-11 | Al completarse una reserva, el sistema debe otorgar **10 puntos** al cliente una sola vez y registrar el movimiento. | Alta | 1.1 |
| RF-12 | El sistema debe asignar un **nivel** (Bronce 0–49, Plata 50–99, Oro ≥ 100) según los puntos acumulados históricos. | Media | 1.1 |
| RF-13 | El cliente debe poder consultar su saldo, nivel, puntos que faltan para el siguiente nivel e historial de movimientos. | Media | 1.1 |
| RF-14 | El cliente debe poder **canjear 50 puntos** por un cupón de 10 % de descuento con código único. | Media | 1.1 |

#### Requisitos modificados

| ID | Cambio |
|---|---|
| RF-09 | El historial de notificaciones incluye ahora los tipos REWARD (puntos ganados) y REDEMPTION (canje). |
| RF-05 / RF-06 | Una reserva COMPLETED no puede modificarse ni cancelarse (igual que una cancelada). |

#### Requisitos no funcionales y restricciones nuevas

| ID | Requisito |
|---|---|
| RNF-08 (Seguridad) | Marcar una reserva como completada requiere la clave de personal (`X-Staff-Key`); sin ella → HTTP 401. |
| RS-07 (Compatibilidad) | La actualización debe conservar los datos de una base de datos v1.0 existente (migración sin pérdida). |

#### Criterios de aceptación nuevos

| ID | Criterio (Dado / Cuando / Entonces) |
|---|---|
| CA-10 | Dada una reserva confirmada ya iniciada, cuando el personal la completa con la clave correcta, entonces su estado es COMPLETED y el cliente suma 10 puntos. |
| CA-11 | Dada una reserva ya completada, cuando se intenta completar otra vez, entonces se obtiene 409 y no se suman puntos. |
| CA-12 | Dado un cliente con 40 puntos acumulados, cuando completa otra reserva, entonces pasa a nivel Plata y la notificación lo indica. |
| CA-13 | Dado un cliente con menos de 50 puntos, cuando intenta canjear, entonces se obtiene 422 y su saldo no cambia. |
| CA-14 | Dado un cliente con 50 puntos, cuando canjea, entonces recibe un cupón `DESC10-XXXXXX`, su saldo baja a 0 y su nivel se mantiene. |
| CA-15 | Dada una BD v1.0 con datos, cuando arranca la v1.1, entonces se migra el esquema y se conservan todas las filas. |

#### Nuevos endpoints

| Método | Ruta | Descripción | RF |
|---|---|---|---|
| POST | `/api/reservations/{code}/complete` (cabecera `X-Staff-Key`) | Marca asistencia y otorga puntos | RF-10, RF-11 |
| GET | `/api/customers/{email}/rewards` | Saldo, nivel e historial | RF-12, RF-13 |
| POST | `/api/customers/{email}/rewards/redeem` | Canje de 50 puntos por cupón | RF-14 |

### 4.1.4 Diseño actualizado (UML v1.1)

- **Diagrama de clases v1.1:** `docs/diagramas/clases_v1_1.puml` / `.png`. Elementos nuevos resaltados en amarillo (`RewardService`, `RewardTransaction`, `RewardType`) y atributos/valores nuevos marcados con "(v1.1)".
- **Diagrama de secuencia v1.1 — "Completar reserva y otorgar puntos":** `docs/diagramas/secuencia_completar_reserva.puml` / `.png`.
- La arquitectura en capas no cambió: el nuevo módulo se agregó como un servicio y un router más, sin tocar `ReservationService`. Esto confirma la decisión de diseño de la Fase 2 (RNF-05).

### 4.1.5 Implementación del cambio

| Archivo | Tipo | Descripción |
|---|---|---|
| `app/models.py` | Modificado | Columnas `points` y `lifetime_points`; entidad `RewardTransaction`; estados y tipos nuevos |
| `app/services/rewards.py` | Nuevo | Reglas de puntos, niveles y canje |
| `app/services/notifications.py` | Modificado | Método `send()` para notificaciones que no dependen de una reserva |
| `app/migrations.py` | Nuevo | Migración v1.0 → v1.1 (ALTER + reconstrucción de `notifications`), idempotente |
| `app/routers/rewards.py` | Nuevo | 3 endpoints; control de clave de personal con `secrets.compare_digest` |
| `app/main.py` | Modificado | Ejecuta la migración al arrancar; versión 1.1.0 |
| `frontend/*` | Modificado | Panel de recompensas con nivel, barra de progreso, historial y botón de canje |

**Evidencias:**

| Archivo | Contenido |
|---|---|
| `migracion_bd_v1_a_v1_1.txt` | La BD de la demo de la Fase 3 (v1.0) se migró al arrancar la v1.1: se agregaron columnas, se reconstruyó `notifications` y se creó `reward_transactions`; **3 reservas, 5 notificaciones y 2 clientes se conservaron**. |
| `demo_recompensas_api.txt` | El personal completa 5 reservas por la API: sin clave → 401; con clave → +10 puntos cada una; a la 5.ª el cliente sube a PLATA; intentar completar dos veces → 409. |
| `notifications_demo_v1_1.log` | 5 notificaciones REWARD y 1 REDEMPTION generadas en la demo. |
| `app_09_recompensas_plata.png` | Panel de recompensas: nivel Plata, 50 puntos, botón de canje habilitado. |
| `app_10_reserva_completada_notificacion.png` | Reserva "Completada" con la notificación "¡Subiste de nivel BRONCE a PLATA!". |
| `app_11_canje_cupon.png` | Canje realizado: cupón `DESC10-8WJGPM`, saldo 0, nivel Plata conservado, historial de movimientos. |

> Para la demo, las 5 reservas `HIST0001`–`HIST0005` (20 al 24/10/2026) se insertaron directamente en la BD de demostración como historial, porque la API solo permite crear reservas futuras y una reserva debe haber iniciado para completarse.

### 4.1.6 Pruebas de regresión

- **Estrategia:** se volvió a ejecutar **sin modificaciones** toda la suite de la Fase 3 (`test_reservation_service.py`, `test_api.py`, 29 pruebas) y se agregó `test_rewards.py` (12 pruebas, TP-28 a TP-39).
- Las pruebas que dependen del paso del tiempo reemplazan el reloj del servicio (`_now`) con `monkeypatch` después de crear las reservas.

| ID | Descripción | Criterio | Resultado |
|---|---|---|---|
| TP-28 | Niveles y puntos para el siguiente nivel en los límites (0, 49, 50, 99, 100) | RF-12 | PASSED |
| TP-29 | Completar otorga 10 puntos, transacción EARN y notificación REWARD | CA-10 | PASSED |
| TP-30 | No se completa una reserva que aún no inicia | RF-10 | PASSED |
| TP-31 | No se otorgan puntos dos veces | CA-11 | PASSED |
| TP-32 | Reserva cancelada no suma puntos | RF-11 | PASSED |
| TP-33 | Sube a Plata con 5 visitas y a Oro con 10; mensaje de subida de nivel | CA-12 | PASSED |
| TP-34 | Canje con puntos insuficientes rechazado sin cambiar saldo | CA-13 | PASSED |
| TP-35 | Canje genera cupón, saldo 0, nivel conservado, notificación sin reserva | CA-14 | PASSED |
| TP-36 | Reserva completada no se modifica ni cancela | RF-05/06 mod. | PASSED |
| TP-37 | API: completar sin clave o con clave incorrecta → 401; con clave → 200 | RNF-08 | PASSED |
| TP-38 | API: resumen de recompensas, canje 422 → 200, cliente inexistente 404 | RF-13, RF-14 | PASSED |
| TP-39 | Migración de una BD con el esquema real v1.0: columnas nuevas, datos conservados, idempotente | CA-15 / RS-07 | PASSED |

**Resultado** (`docs/evidencias/pytest_fase4.txt`): **41 pruebas ejecutadas, 41 aprobadas, 0 fallidas** (≈ 0.9 s). Las 29 pruebas de la Fase 3 siguen aprobando, así que el cambio **no introdujo regresiones**.

### 4.1.7 Clasificación del mantenimiento (SWEBOK)

SWEBOK (área *Software Maintenance*, basada en ISO/IEC 14764) distingue cuatro tipos:

| Tipo | Definición | ¿Aplica a SC-01? |
|---|---|---|
| Correctivo | Corrige fallas descubiertas después de la entrega. | No: no se corrigió ningún defecto. |
| Adaptativo | Ajusta el software a un entorno que cambió (SO, BD, leyes, plataformas). | Solo en parte: la migración adapta la BD existente, pero es consecuencia del cambio, no su causa. |
| **Perfectivo** | Mejora o agrega funcionalidad, rendimiento o mantenibilidad según nuevas necesidades del usuario. | **Sí: es el tipo principal.** |
| Preventivo | Previene problemas futuros (refactorización, documentación) antes de que ocurran. | Complementario: `NotificationService.send()` generaliza el envío y la migración idempotente previene fallos al actualizar. |

**Conclusión:** el sistema de recompensas es **mantenimiento perfectivo**, porque responde a una nueva necesidad del cliente y agrega funcionalidad a un sistema que ya funcionaba correctamente. Según SWEBOK, este tipo de cambio es una **mejora** (*enhancement*), no una corrección.

## 4.2 Revisión y presentación del proyecto

El guion de la presentación final está en `docs/presentacion_final.md` (planificación, requisitos y diseño, interfaces, resultados de pruebas y mantenimiento).

---

## Resumen para el informe

- Se simuló la solicitud de cambio **SC-01**: programa de recompensas para clientes frecuentes. Se acordaron las reglas: 10 puntos por reserva completada; niveles Bronce/Plata/Oro (0/50/100); canje de 50 puntos por un cupón de 10 %.
- ERS actualizada a **v1.1** con historial de versiones: nuevos **RF-10 a RF-14**, **RNF-08** (clave de personal), **RS-07** (migración sin pérdida), RF-09 ampliado y criterios **CA-10 a CA-15**.
- Diseño actualizado: **diagrama de clases v1.1** (`RewardService`, `RewardTransaction`, `RewardType`, estado COMPLETED) y **diagrama de secuencia** "completar reserva y otorgar puntos".
- Implementación: nuevo servicio, router con 3 endpoints, **migración automática e idempotente** de la BD v1.0 y panel de recompensas en el frontend.
- La migración se probó sobre la BD real de la demo de la Fase 3: se conservaron 3 reservas, 5 notificaciones y 2 clientes.
- **Regresión: 41/41 pruebas aprobadas**: las 29 de la Fase 3 sin cambios + 12 nuevas (TP-28 a TP-39); salida en `pytest_fase4.txt`.
- Demo por API y por interfaz: subida de Bronce a Plata con notificación, rechazo sin clave (401) o por doble registro (409), canje del cupón `DESC10-8WJGPM`.
- Clasificación SWEBOK: **mantenimiento perfectivo** (nueva funcionalidad pedida por el cliente), con aspectos preventivos y adaptativos secundarios.
