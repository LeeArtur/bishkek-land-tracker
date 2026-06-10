import statistics
from datetime import date
from sqlalchemy.orm import Session
from db.models import District, Listing, PriceHistory
from scraper.base import ListingRaw

# Regions outside Bishkek + Chui — skip listings from these areas
_EXCLUDED_REGIONS = {
    "иссык-кульская", "ошская", "джалал-абадская",
    "нарынская", "баткенская", "таласская",
    "иссык-куль", "ош", "джалал-абад", "нарын", "баткен", "талас",
}

def _is_bishkek_or_chui(district_name: str) -> bool:
    """Return False if the address clearly points to another region."""
    lower = district_name.lower()
    return not any(excl in lower for excl in _EXCLUDED_REGIONS)


def _get_or_create_district(db: Session, name: str) -> District:
    district = db.query(District).filter_by(name=name).first()
    if not district:
        district = District(name=name)
        db.add(district)
        db.flush()
    return district


def upsert_listing(db: Session, raw: ListingRaw, today: date) -> None:
    """Upsert one listing. Does NOT commit — caller owns the transaction."""
    if raw.price_usd is None or raw.area_sotka is None or raw.area_sotka <= 0:
        return

    district = _get_or_create_district(db, raw.district_name)
    price_per_sotka = raw.price_usd / raw.area_sotka

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
            published_at=raw.published_at,
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
        existing.district_id = district.id
        if raw.published_at and not existing.published_at:
            existing.published_at = raw.published_at
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


def mark_inactive(db: Session, seen_external_ids: set, today: date) -> None:
    """Mark active listings absent from seen_external_ids as inactive."""
    active = db.query(Listing).filter_by(is_active=True).all()
    for listing in active:
        if listing.external_id not in seen_external_ids:
            listing.is_active = False
    db.commit()


def recalculate_districts(db: Session) -> None:
    """Recalculate avg, median, count for all districts from active listings."""
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
            district.avg_price_per_sotka = None
            district.median_price_per_sotka = None
            district.listing_count = 0
    db.commit()


def run_scrape(db: Session, scrapers: list) -> dict:
    """
    scrapers: list of (name: str, fn: () -> list[ListingRaw])
    Only marks listings inactive for sources that succeeded (failed scrapers
    don't pollute seen_ids, preventing accidental de-listing).
    Returns dict of {source_name: {count, error}}.
    """
    today = date.today()
    seen_external_ids: set = set()
    results = {}
    failed_sources: set = set()

    for name, scraper_fn in scrapers:
        try:
            raw_listings = scraper_fn()
            filtered = [r for r in raw_listings if _is_bishkek_or_chui(r.district_name)]
            for raw in filtered:
                upsert_listing(db, raw, today)
                seen_external_ids.add(raw.external_id)
            db.commit()
            results[name] = {"count": len(filtered), "skipped": len(raw_listings) - len(filtered), "error": None}
        except Exception as e:
            db.rollback()
            failed_sources.add(name)
            results[name] = {"count": 0, "error": str(e)}

    if failed_sources:
        # Don't mark inactive for listings belonging to failed scrapers,
        # to avoid de-listing valid inventory due to a transient scraper error.
        failed_ids = {
            l.external_id
            for l in db.query(Listing).filter(Listing.source.in_(failed_sources)).all()
        }
        seen_external_ids |= failed_ids

    mark_inactive(db, seen_external_ids, today)
    recalculate_districts(db)
    return results
