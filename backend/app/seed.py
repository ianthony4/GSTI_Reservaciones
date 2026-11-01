"""Datos iniciales: 3 sucursales con sus mesas (según acta de reunión)."""
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Restaurant, Table

BRANCHES = [
    ("Sabores del Sur - Centro", "Calle Mercaderes 210, Cercado, Arequipa", "054 201010"),
    ("Sabores del Sur - Cayma", "Av. Ejército 1020, Cayma, Arequipa", "054 202020"),
    ("Sabores del Sur - Yanahuara", "Plaza de Yanahuara 105, Arequipa", "054 203030"),
]
# (número, capacidad, ubicación)
TABLES = [(1, 2, "Ventana"), (2, 2, "Ventana"), (3, 4, "Salón"), (4, 4, "Salón"),
          (5, 6, "Terraza"), (6, 8, "Salón privado")]


def seed(db: Session) -> None:
    if db.scalar(select(Restaurant.id)) is not None:
        return
    for name, address, phone in BRANCHES:
        r = Restaurant(name=name, address=address, phone=phone,
                       opening_time=time(12, 0), closing_time=time(23, 0))
        r.tables = [Table(number=n, capacity=c, location=loc) for n, c, loc in TABLES]
        db.add(r)
    db.commit()
