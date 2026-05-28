from datetime import date
from db.models import District, Listing, PriceHistory, MacroData


def test_seed_creates_districts(db):
    districts = db.query(District).all()
    names = [d.name for d in districts]
    assert "Октябрьский" in names
    assert "Ленинский" in names
    assert len(districts) == 6


def test_listing_relates_to_district(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:001",
        source="house.kg",
        title="Участок 8 соток",
        district_id=district.id,
        area_sotka=8.0,
        current_price_usd=12000.0,
        price_per_sotka=1500.0,
        url="https://house.kg/listing/001",
        first_seen=date(2026, 5, 28),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    assert listing.district.name == "Ленинский"


def test_price_history_links_to_listing(db):
    district = db.query(District).filter_by(name="Ленинский").first()
    listing = Listing(
        external_id="house.kg:002",
        source="house.kg",
        title="Участок",
        district_id=district.id,
        area_sotka=6.0,
        current_price_usd=10000.0,
        price_per_sotka=1666.67,
        url="https://house.kg/002",
        first_seen=date(2026, 5, 1),
        last_seen=date(2026, 5, 28),
        is_active=True,
    )
    db.add(listing)
    db.flush()
    ph = PriceHistory(
        listing_id=listing.id,
        price_usd=10000.0,
        price_per_sotka=1666.67,
        recorded_at=date(2026, 5, 28),
        change_pct=None,
    )
    db.add(ph)
    db.commit()
    assert listing.history[0].change_pct is None
