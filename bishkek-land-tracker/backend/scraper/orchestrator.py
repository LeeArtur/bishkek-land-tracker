import statistics
from datetime import date
from sqlalchemy.orm import Session
from db.models import District, Listing, PriceHistory
from scraper.base import ListingRaw


def _get_or_create_district(db: Session, name: str) -> District:
    district = db.query(District).filter_by(name=name).first()
    if not district:
        district = District(name=name)
        db.add(district)
        db.flush()
    return district


def upsert_listing(db: Session, raw: ListingRaw, today: date) -> None:
    district = _get_or_create_district(db, raw.district_name)
    price_per_sotka = (raw.price_usd / raw.area_sotka) if (raw.area_sotka and raw.area_sotka > 0) else 0.0

    existing = db.query(Listing).filter_by(external_id=raw.external_id).first()

    if not existing:
        listing = Listing(
            external_id=raw.external_id,
            source=raw.source,
            title=raw.title,
            district_id=district.id,
            area_sotka=raw.area_sotka,
            current_price_usd=raw.price_usd,
            price_per_sotka=price_per_sotka,
            url=raw.url,
            first_seen=today,
            last_seen=today,
            is_active=True,
        )
        db.add(listing)
        db.flush()
        db.add(PriceHistory(
            listing_id=listing.id,
            price_usd=raw.price_usd,
            price_per_sotka=price_per_sotka,
            recorded_at=today,
            change_pct=None,
        ))
    else:
        existing.last_seen = today
        existing.is_active = True
        if existing.current_price_usd != raw.price_usd:
            change_pct = ((raw.price_usd - existing.current_price_usd) / existing.current_price_usd) * 100
            existing.current_price_usd = raw.price_usd
            existing.price_per_sotka = price_per_sotka
            db.add(PriceHistory(
                listing_id=existing.id,
                price_usd=raw.price_usd,
                price_per_sotka=price_per_sotka,
                recorded_at=today,
                change_pct=change_pct,
            ))

    db.commit()


def mark_inactive(db: Session, seen_external_ids: set, today: date) -> None:
    active = db.query(Listing).filter_by(is_active=True).all()
    for listing in active:
        if listing.external_id not in seen_external_ids:
            listing.is_active = False
    db.commit()


def recalculate_districts(db: Session) -> None:
    districts = db.query(District).all()
    for district in districts:
        prices = [
            l.price_per_sotka
            for l in db.query(Listing).filter_by(district_id=district.id, is_active=True).all()
            if l.price_per_sotka and l.price_per_sotka > 0
        ]
        if prices:
            district.avg_price_per_sotka = sum(prices) / len(prices)
            district.median_price_per_sotka = statistics.median(prices)
            district.listing_count = len(prices)
        else:
            district.listing_count = 0
    db.commit()


def run_scrape(db: Session, scrapers: list) -> dict:
    """
    scrapers: list of (name: str, fn: () -> list[ListingRaw])
    Returns dict of {source_name: {count, error}}
    """
    today = date.today()
    seen_external_ids: set = set()
    results = {}

    for name, scraper_fn in scrapers:
        try:
            raw_listings = scraper_fn()
            for raw in raw_listings:
                upsert_listing(db, raw, today)
                seen_external_ids.add(raw.external_id)
            results[name] = {"count": len(raw_listings), "error": None}
        except Exception as e:
            results[name] = {"count": 0, "error": str(e)}

    mark_inactive(db, seen_external_ids, today)
    recalculate_districts(db)
    return results
