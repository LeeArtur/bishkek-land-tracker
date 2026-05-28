from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import District

router = APIRouter()


@router.get("/districts")
def get_districts(db: Session = Depends(get_db)):
    districts = db.query(District).order_by(District.name).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "avg_price_per_sotka": d.avg_price_per_sotka,
            "median_price_per_sotka": d.median_price_per_sotka,
            "listing_count": d.listing_count,
        }
        for d in districts
    ]
