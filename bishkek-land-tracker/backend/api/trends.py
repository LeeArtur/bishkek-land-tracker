from datetime import date, timedelta
from collections import defaultdict
import statistics
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import PriceHistory, Listing, District

router = APIRouter()


@router.get("/trends")
def get_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=365),
):
    since = date.today() - timedelta(days=days)

    rows = (
        db.query(PriceHistory, Listing, District)
        .join(Listing, PriceHistory.listing_id == Listing.id)
        .join(District, Listing.district_id == District.id)
        .filter(PriceHistory.recorded_at >= since)
        .all()
    )

    buckets: dict[tuple, list[float]] = defaultdict(list)
    district_names: dict[int, str] = {}
    for ph, listing, district in rows:
        key = (str(ph.recorded_at), district.id)
        buckets[key].append(ph.price_per_sotka)
        district_names[district.id] = district.name

    result = []
    for (recorded_at, district_id), prices in sorted(buckets.items()):
        result.append({
            "date": recorded_at,
            "district_id": district_id,
            "district_name": district_names[district_id],
            "median_price_per_sotka": round(statistics.median(prices), 2),
            "sample_count": len(prices),
        })

    return result
