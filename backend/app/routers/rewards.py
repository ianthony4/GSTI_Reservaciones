"""v1.1 - Endpoints del programa de recompensas (RF-10 a RF-14)."""
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CompletionOut, RedemptionOut, RewardSummaryOut
from ..services.rewards import COUPON_BENEFIT, REDEEM_COST, RewardService, level_for

router = APIRouter(tags=["Recompensas (v1.1)"])


def require_staff(x_staff_key: str = Header(default="")) -> None:
    """RNF-08: solo el personal del restaurante (clave de personal) marca asistencias."""
    expected = os.getenv("RESERVAYA_STAFF_KEY", "staff-demo-key")
    if not secrets.compare_digest(x_staff_key, expected):
        raise HTTPException(status_code=401, detail="Clave de personal inválida")


@router.post("/api/reservations/{code}/complete", response_model=CompletionOut,
             dependencies=[Depends(require_staff)])
def complete_reservation(code: str, db: Session = Depends(get_db)):
    reservation, tx = RewardService(db).complete_reservation(code)
    c = reservation.customer
    return CompletionOut(code=reservation.code, status=reservation.status, points_earned=tx.points,
                         customer_points=c.points, customer_level=level_for(c.lifetime_points))


@router.get("/api/customers/{email}/rewards", response_model=RewardSummaryOut)
def rewards_summary(email: str, db: Session = Depends(get_db)):
    return RewardService(db).summary(email)


@router.post("/api/customers/{email}/rewards/redeem", response_model=RedemptionOut)
def redeem(email: str, db: Session = Depends(get_db)):
    tx = RewardService(db).redeem(email)
    return RedemptionOut(coupon_code=tx.coupon_code, points_spent=REDEEM_COST,
                         remaining_points=tx.customer.points, benefit=COUPON_BENEFIT)
