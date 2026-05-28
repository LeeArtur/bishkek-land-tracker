from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import MacroData

router = APIRouter()


@router.get("/macro")
def get_macro(db: Session = Depends(get_db)):
    latest = db.query(MacroData).order_by(MacroData.recorded_at.desc()).first()
    if not latest:
        return None
    return {
        "recorded_at": str(latest.recorded_at),
        "usd_kgs_rate": latest.usd_kgs_rate,
        "source": latest.source,
    }
