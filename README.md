# ReservaYa — Sistema de reservas para una cadena de restaurantes

Laboratorio 04 del curso **Gestión de Sistemas y Tecnologías de Información** (UNSA – EPIS):
*Proceso de Desarrollo de Software basado en SWEBOK*.

Aplicación web para **reservar, consultar, modificar y cancelar** mesas en las sucursales de la cadena
"Sabores del Sur", con **notificaciones de confirmación** simuladas y, desde la v1.1, un **programa de
recompensas** para clientes frecuentes.

- **Backend:** Python 3.10+ · FastAPI · SQLAlchemy · SQLite
- **Frontend:** HTML, CSS y JavaScript (sin frameworks), servido por el mismo backend
- **Pruebas:** pytest + `fastapi.testclient`

## Instalación

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r backend/requirements.txt
```

## Ejecución

```bash
cd backend
uvicorn app.main:app --reload
```

- Aplicación web: <http://127.0.0.1:8000/>
- Documentación de la API (OpenAPI): <http://127.0.0.1:8000/docs>

Al arrancar se crea `backend/reservaya.db` con 3 sucursales y 6 mesas por sucursal. Si existe una BD v1.0,
se migra automáticamente a v1.1. Las notificaciones se registran en la BD y en `backend/notifications.log`.

Variables de entorno opcionales:

| Variable | Por defecto | Uso |
|---|---|---|
| `RESERVAYA_DB` | `sqlite:///./reservaya.db` | URL de la base de datos |
| `RESERVAYA_NOTIF_LOG` | `notifications.log` | Archivo de log de notificaciones |
| `RESERVAYA_STAFF_KEY` | `staff-demo-key` | Clave de personal para `POST /api/reservations/{code}/complete` (cambiarla fuera de la demo) |
| `CORS_ORIGINS` | `*` | Orígenes que pueden llamar a la API, separados por comas (p. ej. `https://usuario.github.io`) |

Ejemplo de cómo el personal marca una reserva como completada (otorga 10 puntos):

```bash
curl -X POST -H "X-Staff-Key: staff-demo-key" http://127.0.0.1:8000/api/reservations/CODIGO/complete
```

## Pruebas

```bash
cd backend
python -m pytest -v
```

Resultado actual: **41 pruebas aprobadas** (ver `docs/evidencias/pytest_fase4.txt`).

## Estructura

```
lab04/
├── backend/            API FastAPI (app/), pruebas (tests/), requirements.txt
├── frontend/           index.html, styles.css, app.js
├── mockups/            wireframes de baja fidelidad (HTML)
├── docs/
│   ├── fase1_planificacion.md
│   ├── fase2_requisitos_diseno.md
│   ├── fase3_construccion_pruebas.md
│   ├── fase4_mantenimiento.md
│   ├── presentacion_final.md
│   ├── diagramas/      UML en PlantUML (.puml) + PNG
│   └── evidencias/     capturas, salidas de pytest, logs
├── informe_04.md       guía original del laboratorio
├── instrucciones.md
└── Informe_Lab04.docx  informe final
```

Para regenerar los diagramas: `java -jar plantuml.jar -tpng docs/diagramas/*.puml`.


## Demo en línea

GitHub Pages solo sirve archivos estáticos, así que el sistema se publica en dos partes:

| Parte | Servicio | Archivo |
|---|---|---|
| Frontend | GitHub Pages | `.github/workflows/pages.yml` |
| API (FastAPI + SQLite) | Render (plan gratuito) | `render.yaml` |
| Pruebas en cada push | GitHub Actions | `.github/workflows/ci.yml` |
| Releases con el informe adjunto | GitHub Actions | `.github/workflows/release.yml` 