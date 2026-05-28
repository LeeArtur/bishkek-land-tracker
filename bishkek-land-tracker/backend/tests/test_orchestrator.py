from datetime import date
from db.models import Listing, PriceHistory, District
from scraper.base import ListingRaw
from scraper.orchestrator import upsert_listing, mark_inactive, recalculate_districts


def _make_raw(external_id="house.kg:001", price=12000.0, area=8.0, district="Ленинский"):
    return ListingRaw(
        external_id=external_id,
        source="house.kg",
        title="Участок",
        district_name=district,
        area_sotka=area,
        price_usd=price,
        url=f"https://house.kg/{external_id}",
        scraped_at=date(2026, 5, 28),
    )


def test_upsert_new_listing_creates_record(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert listing is not None
    assert listing.current_price_usd == 12000.0
    assert listing.price_per_sotka == 1500.0
    assert listing.is_active is True


def test_upsert_new_listing_creates_price_history(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert len(listing.history) == 1
    assert listing.history[0].change_pct is None


def test_upsert_existing_no_change_does_not_add_history(db):
    raw = _make_raw()
    upsert_listing(db, raw, date(2026, 5, 27))
    upsert_listing(db, raw, date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert len(listing.history) == 1
    assert listing.last_seen == date(2026, 5, 28)


def test_upsert_price_change_adds_history_with_pct(db):
    upsert_listing(db, _make_raw(price=12000.0), date(2026, 5, 27))
    upsert_listing(db, _make_raw(price=10000.0), date(2026, 5, 28))
    listing = db.query(Listing).filter_by(external_id="house.kg:001").first()
    assert listing.current_price_usd == 10000.0
    assert len(listing.history) == 2
    last_record = max(listing.history, key=lambda h: h.recorded_at)
    assert round(last_record.change_pct, 2) == round(((10000 - 12000) / 12000) * 100, 2)


def test_mark_inactive_removes_missing_listings(db):
    upsert_listing(db, _make_raw("house.kg:001"), date(2026, 5, 28))
    upsert_listing(db, _make_raw("house.kg:002"), date(2026, 5, 28))
    mark_inactive(db, seen_external_ids={"house.kg:001"}, today=date(2026, 5, 29))
    l1 = db.query(Listing).filter_by(external_id="house.kg:001").first()
    l2 = db.query(Listing).filter_by(external_id="house.kg:002").first()
    assert l1.is_active is True
    assert l2.is_active is False


def test_recalculate_districts_sets_median(db):
    for ext_id, price in [("h:1", 10000.0), ("h:2", 14000.0), ("h:3", 18000.0)]:
        upsert_listing(db, _make_raw(ext_id, price=price, area=10.0, district="Октябрьский"), date(2026, 5, 28))
    recalculate_districts(db)
    d = db.query(District).filter_by(name="Октябрьский").first()
    assert d.median_price_per_sotka == 1400.0
    assert d.listing_count == 3
