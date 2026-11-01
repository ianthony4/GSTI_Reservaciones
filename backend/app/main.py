"""Punto de entrada de la API ReservaYa."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import SessionLocal, engine
from .migrations import migrate
from .routers import customers, reservations, restaurants, rewards
from .seed import seed
from .services.errors import BusinessError

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    for step in migrate(engine):  # v1.1: crea tablas nuevas y migra una BD v1.0 existente
        print(f"[migración] {step}")
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="ReservaYa API", version="1.1.0",
              description="Sistema de reservas en línea para una cadena de restaurantes (Lab 04 - SWEBOK)",
              lifespan=lifespan)


# CORS: permite que el frontend publicado en otro dominio (p. ej. GitHub Pages) consuma la API.
# CORS_ORIGINS = lista separada por comas, p. ej. "https://usuario.github.io". Por defecto "*".
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=False)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(restaurants.router)
app.include_router(reservations.router)
app.include_router(customers.router)
app.include_router(rewards.router)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
