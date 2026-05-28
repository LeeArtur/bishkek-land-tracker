from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Listing, PriceHistory

router = APIRouter()


def _listing_to_dict(l: Listing, price_changed_today: bool = False, change_pct_today: float | None = None) -> dict:
    return {
        "id": l.id,
        "external_id": l.external_id,
        "source": l.source,
        "title": l.title,
        "district_id": l.district_id,
        "district_name": l.district.name if l.district else "",
        "area_sotka": l.area_sotka,
        "current_price_usd": l.current_price_usd,
        "price_per_sotka": l.price_per_sotka,
        "url": l.url,
        "first_seen": str(l.first_seen),
        "last_seen": str(l.last_seen),
        "is_active": l.is_active,
        "price_changed_today": price_changed_today,
        "change_pct_today": change_pct_today,
    }


@router.get("/listings")
def get_listings(
    db: Session = Depends(get_db),
    district_id: int | None = Query(None),
    source: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    min_area: float | None = Query(None),
    max_area: float | None = Query(None),
    price_changed_today: bool = Query(False),
):
    today = date.today()
    today_changes = {
        ph.listing_id: ph.change_pct
        for ph in db.query(PriceHistory).filter(
            PriceHistory.recorded_at == today,
            PriceHistory.change_pct != None,
        ).all()
    }

    q = db.query(Listing).filter_by(is_active=True)
    if district_id is not None:
        q = q.filter(Listing.district_id == district_id)
    if source:
        q = q.filter(Listing.source == source)
    if min_price is not None:
        q = q.filter(Listing.current_price_usd >= min_price)
    if max_price is not None:
        q = q.filter(Listing.current_price_usd <= max_price)
    if min_area is not None:
        q = q.filter(Listing.area_sotka >= min_area)
    if max_area is not None:
        q = q.filter(Listing.area_sotka <= max_area)
    if price_changed_today:
        q = q.filter(Listing.id.in_(today_changes.keys()))

    listings = q.order_by(Listing.price_per_sotka).all()
    return [
        _listing_to_dict(l, l.id in today_changes, today_changes.get(l.id))
        for l in listings
    ]


@router.get("/listings/{listing_id}/history")
def get_listing_history(listing_id: int, db: Session = Depends(get_db)):
    history = (
        db.query(PriceHistory)
        .filter_by(listing_id=listing_id)
        .order_by(PriceHistory.recorded_at)
        .all()
    )
    return [
        {
            "price_usd": h.price_usd,
            "price_per_sotka": h.price_per_sotka,
            "recorded_at": str(h.recorded_at),
            "change_pct": h.change_pct,
        }
        for h in history
    ]
