from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Listing, District
from config import DEAL_THRESHOLD, is_residential

router = APIRouter()


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    districts = {d.id: d for d in db.query(District).all()}
    listings = db.query(Listing).filter_by(is_active=True).all()

    deals = []
    for l in listings:
        if not is_residential(l.title or ""):
            continue
        if l.area_sotka and l.area_sotka > 50:
            continue
        district = districts.get(l.district_id)
        if not district or not district.median_price_per_sotka:
            continue
        threshold = district.median_price_per_sotka * DEAL_THRESHOLD
        if l.price_per_sotka and l.price_per_sotka < threshold:
            discount_pct = round(
                (1 - l.price_per_sotka / district.median_price_per_sotka) * 100, 1
            )
            deals.append({
                "id": l.id,
                "external_id": l.external_id,
                "source": l.source,
                "title": l.title,
                "district_id": l.district_id,
                "district_name": district.name,
                "area_sotka": l.area_sotka,
                "current_price_usd": l.current_price_usd,
                "price_per_sotka": l.price_per_sotka,
                "median_price_per_sotka": district.median_price_per_sotka,
                "discount_pct": discount_pct,
                "url": l.url,
                "last_seen": str(l.last_seen),
            })

    return sorted(deals, key=lambda d: d["discount_pct"], reverse=True)
