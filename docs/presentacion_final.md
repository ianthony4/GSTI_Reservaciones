# Guion de la presentación final — ReservaYa (Lab 04, SWEBOK)

Duración sugerida: **12–15 minutos** + preguntas. Una diapositiva por punto.

## 1. Portada (0:30)
- "ReservaYa: sistema de reservas en línea para una cadena de restaurantes".
- Integrantes, curso y docente.

## 2. SWEBOK y modelo de proceso (1:30) — *Fase 1*
- Las 7 áreas de SWEBOK usadas y dónde se aplicó cada una (tabla de la Fase 1).
- Modelo **iterativo-incremental** con 4 iteraciones; justificación: se esperaba un cambio de requisitos.
- Estimación: 15 actividades, 21 h; mostrar el **diagrama de Gantt** (`cronograma_gantt.png`).
- Riesgo principal: cambio de requisitos (R1), mitigado con el modelo iterativo y el diseño en capas.

## 3. Requisitos (2:00) — *Fase 2*
- Reunión con el cliente (simulada): 11 preguntas y sus reglas (horario 12–23 h, 2 h por reserva, 60 días).
- ERS: **9 RF, 7 RNF, 6 restricciones**; ejemplo RF-03 frente a RNF-03.
- Diagrama de **casos de uso** y un criterio de aceptación en formato Dado/Cuando/Entonces.

## 4. Diseño (2:00) — *Fase 2*
- Arquitectura en 4 capas (`arquitectura.png`).
- **Diagrama de clases** (5 entidades + 2 servicios).
- **Diagrama de secuencia** "crear reserva y notificar": flujo normal y alternativo 409.

## 5. Interfaces (2:00) — *Fase 3*
- Del **mockup** a la pantalla real: Reservar → Confirmación → Mis reservas (mostrar las parejas de imágenes).
- Demo en vivo (opcional): `uvicorn app.main:app` → reservar → modificar → cancelar → ver notificaciones.
- Vista móvil (responsive).

## 6. Construcción y pruebas (2:00) — *Fase 3*
- Reglas implementadas: no solapamiento, asignación de la mesa más pequeña disponible, validaciones.
- Plan de pruebas: 27 casos trazados a RF/RNF/CA.
- Resultado: **29/29 aprobadas** (`pytest_fase3.txt`); tiempos de respuesta < 10 ms.

## 7. Mantenimiento (2:30) — *Fase 4*
- Solicitud de cambio SC-01: recompensas (10 puntos por visita, Bronce/Plata/Oro, cupón 10 % por 50 puntos).
- ERS v1.1 con historial; UML v1.1 (clases + secuencia "completar reserva").
- Migración de la BD sin pérdida de datos (evidencia real).
- Regresión: **41/41 aprobadas**, sin regresiones.
- Clasificación SWEBOK: **perfectivo**.

## 8. Conclusiones y lecciones aprendidas (1:00)
- SWEBOK como mapa: cada fase produjo entregables verificables.
- La arquitectura en capas y las pruebas automatizadas abarataron el cambio de requisitos.
- Mejoras futuras: envío real de correo (SMTP), autenticación de clientes, panel administrativo.

## 9. Preguntas
